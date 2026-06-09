from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain_community.chat_models import ChatTongyi

import config_data as config
from app_backend.models import LibraryRecord, MemoryRecord, SessionRecord
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.services.config_service import ConfigService
from app_backend.services.external_search_service import (
    ExternalPaperCandidate,
    ExternalSearchService,
    NullExternalSearchService,
)
from app_backend.services.external_search_planner_service import (
    ExternalSearchPlan,
    ExternalSearchPlannerService,
)
from app_backend.services.memory_service import MemoryService
from app_backend.services.retriever_service import RetrieverService


_JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")


@dataclass
class CoverageAssessment:
    """描述本地文献证据是否足以支持当前回答。"""

    sufficient: bool
    should_search_external: bool
    reason_codes: list[str] = field(default_factory=list)
    local_unique_documents: int = 0
    max_rerank_score: float | None = None
    avg_rerank_score: float | None = None
    freshness_gap_detected: bool = False
    recommended_external_limit: int = 0
    useful_local_evidence_ids: list[str] = field(default_factory=list)
    discarded_local_evidence_ids: list[str] = field(default_factory=list)
    rationale: str = ""
    evaluator: str = "llm"


@dataclass
class PendingIngestRecord:
    """记录外部候选文献后续是否需要进入文献库。"""

    external_id: str
    title: str
    library_id: int | None
    decision: str
    reason: str
    job_id: int | None = None


@dataclass
class AgentActionRecord:
    """记录 agent 在编排过程中执行过的动作。"""

    action: str
    status: str
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratedChatContext:
    """聚合一次问答编排阶段得到的全部上下文。"""

    session: SessionRecord
    library: LibraryRecord | None
    user_message: str
    retrieved_memories: list[MemoryRecord]
    local_documents: list[dict[str, Any]]
    external_documents: list[dict[str, Any]]
    selected_documents: list[dict[str, Any]]
    retrieval_mode: str
    coverage: CoverageAssessment
    actions: list[AgentActionRecord] = field(default_factory=list)
    pending_ingest: list[PendingIngestRecord] = field(default_factory=list)
    local_retrieval_trace: dict[str, Any] = field(default_factory=dict)
    external_rerank_trace: dict[str, Any] = field(default_factory=dict)

    def to_prompt_payload(self) -> dict[str, Any]:
        """把编排结果转换为提示词和前端可直接消费的字典。"""
        return {
            "session": self.session,
            "library": self.library,
            "memories": self.retrieved_memories,
            "retrieved_docs": self.selected_documents,
            "retrieval_mode": self.retrieval_mode,
            "coverage": asdict(self.coverage),
            "agent_actions": [asdict(item) for item in self.actions],
            "pending_ingest": [asdict(item) for item in self.pending_ingest],
        }


@dataclass
class AgentEvent:
    """表示一次流式编排过程中的阶段事件。"""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    context: Any | None = None


class AgentOrchestratorService:
    """编排本地检索、外部检索和候选入库决策的服务。"""

    def __init__(
        self,
        session_repository: SessionRepository,
        library_repository: LibraryRepository,
        memory_service: MemoryService,
        retriever_service: RetrieverService,
        config_service: ConfigService | None = None,
        external_search_service: ExternalSearchService | None = None,
        external_search_planner_service: ExternalSearchPlannerService | None = None,
    ) -> None:
        """初始化编排服务，并注入本地检索与外部检索依赖。"""
        self.session_repository = session_repository
        self.library_repository = library_repository
        self.memory_service = memory_service
        self.retriever_service = retriever_service
        self.config_service = config_service
        self.external_search_service = external_search_service or NullExternalSearchService()
        self.external_search_planner_service = external_search_planner_service

    def stream_prepare_chat_context(
        self,
        session_id: int,
        user_message: str,
        external_search_only: bool = False,
        allow_external_search: bool = False,
    ) -> Iterator[AgentEvent]:
        """以事件形式输出上下文准备进度，并在最后返回完整上下文。"""
        started_at = time.perf_counter()
        yield AgentEvent(type="prepare_start", payload={})

        session = self._require_session(session_id)
        library = self._get_optional_library(session.library_id)
        memories = self.memory_service.recall_memories(user_message, session_id=session_id, limit=5)
        # 最终进入上下文的证据总量统一由 MAX_SEARCH_NUM 控制，避免再叠加单篇文献分块上限。
        effective_top_k = config.MAX_SEARCH_NUM

        if library is None:
            local_documents = []
            local_retrieval_trace: dict[str, Any] = {}
            actions = self._build_no_library_actions(effective_top_k, allow_external_search=allow_external_search)
            coverage = CoverageAssessment(
                sufficient=not allow_external_search,
                should_search_external=allow_external_search,
                reason_codes=["no_library_bound"] if allow_external_search else [],
                local_unique_documents=0,
                recommended_external_limit=max(effective_top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT)
                if allow_external_search
                else 0,
                rationale="会话未绑定文献库，因此无法执行本地证据充分性判断。",
                evaluator="system",
            )
        elif external_search_only:
            local_documents: list[dict[str, Any]] = []
            local_retrieval_trace = {}
            actions = self._build_external_only_actions(library.id, effective_top_k)
            coverage = CoverageAssessment(
                sufficient=False,
                should_search_external=True,
                reason_codes=["external_search_requested"],
                local_unique_documents=0,
                recommended_external_limit=max(effective_top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT),
                rationale="当前请求指定只进行外部检索，跳过本地证据充分性判断。",
                evaluator="system",
            )
        else:
            yield AgentEvent(
                type="prepare_step",
                payload={"step": self._build_library_prepare_step(library.name, "running", 0)},
            )
            local_documents, local_retrieval_trace = self._search_local_documents_with_trace(
                user_message=user_message,
                library_id=library.id,
                top_k=effective_top_k,
            )
            yield AgentEvent(
                type="prepare_step",
                payload={
                    "step": self._build_library_prepare_step(
                        library.name,
                        "success",
                        self._count_unique_documents(local_documents),
                    )
                },
            )
            actions = [
                AgentActionRecord(
                    action="local_search",
                    status="completed",
                    detail=f"Retrieved {len(local_documents)} local evidence chunks.",
                    payload={
                        "library_id": library.id,
                        "local_recall_k": self._get_recall_chunks(),
                        "local_rerank_k": effective_top_k,
                    },
                )
            ]
            if allow_external_search:
                yield AgentEvent(
                    type="prepare_step",
                    payload={"step": self._build_coverage_prepare_step("running")},
                )
                try:
                    coverage = self._assess_local_coverage_with_llm(
                        user_message=user_message,
                        local_documents=local_documents,
                        top_k=effective_top_k,
                    )
                except Exception as exc:
                    yield AgentEvent(
                        type="prepare_step",
                        payload={
                            "step": self._build_coverage_prepare_step(
                                "error",
                                error=f"本地文献充分性判断失败：{exc}",
                            )
                        },
                    )
                    raise RuntimeError(f"本地文献充分性判断失败：{exc}") from exc
                yield AgentEvent(
                    type="prepare_step",
                    payload={"step": self._build_coverage_prepare_step("success", coverage=coverage)},
                )
                actions.append(
                    AgentActionRecord(
                        action="coverage_assessment",
                        status="completed",
                        detail="LLM assessed whether local evidence is sufficient.",
                        payload=asdict(coverage),
                    )
                )
            else:
                coverage = self._build_local_only_coverage(local_documents)
                actions.append(
                    AgentActionRecord(
                        action="coverage_assessment",
                        status="skipped",
                        detail="Skipped LLM coverage assessment because external search is disabled.",
                        payload=asdict(coverage),
                    )
                )

        external_documents: list[dict[str, Any]] = []
        external_rerank_trace: dict[str, Any] = {}
        pending_ingest: list[PendingIngestRecord] = []
        useful_local_documents = self._filter_useful_local_documents(local_documents, coverage)
        merged_useful_local_documents = self._merge_adjacent_useful_local_chunks(useful_local_documents)
        external_search_attempted = allow_external_search and coverage.should_search_external

        if external_search_attempted:
            yield AgentEvent(
                type="prepare_step",
                payload={"step": self._build_search_plan_prepare_step("running")},
            )
            try:
                search_plan = self._build_external_search_plan(
                    user_message,
                    limit=coverage.recommended_external_limit or max(effective_top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT),
                    freshness_requested=coverage.freshness_gap_detected,
                )
            except Exception as exc:
                yield AgentEvent(
                    type="prepare_step",
                    payload={
                        "step": self._build_search_plan_prepare_step(
                            "error",
                            error=f"外部检索计划生成失败：{exc}",
                        )
                    },
                )
                raise RuntimeError(f"外部检索计划生成失败：{exc}") from exc
            yield AgentEvent(
                type="prepare_step",
                payload={"step": self._build_search_plan_prepare_step("success", search_plan=search_plan)},
            )
            external_candidates: list[ExternalPaperCandidate] = []
            for search_event in self.external_search_service.iter_search_papers_batch(
                search_plan.to_search_kwargs_list(),
                final_limit=search_plan.final_limit,
            ):
                event_type = str(search_event.get("type") or "")
                if event_type == "search_batch_done":
                    candidates = search_event.get("candidates")
                    external_candidates = candidates if isinstance(candidates, list) else []
                    continue
                yield AgentEvent(
                    type="prepare_step",
                    payload={"step": self._build_prepare_step_from_search_event(search_event)},
                )

            actions.append(
                AgentActionRecord(
                    action="external_search",
                    status="completed" if external_candidates else "skipped",
                    detail="Searched external sources for supplementary evidence."
                    if external_candidates
                    else "External search returned no candidates.",
                    payload={
                        "candidate_count": len(external_candidates),
                        "search_plan": search_plan.to_dict(),
                    },
                )
            )
            external_documents = self._prepare_external_documents(local_documents, external_candidates)
            external_quota = self._calculate_external_evidence_quota(merged_useful_local_documents)
            external_documents, external_rerank_trace = self._rerank_external_documents_with_trace(
                user_message,
                external_documents,
                external_quota=external_quota,
            )
            if library is not None:
                pending_ingest = self.decide_ingest_candidates(
                    library_id=library.id,
                    external_candidates=external_candidates,
                    user_message=user_message,
                )
        elif coverage.should_search_external and not allow_external_search:
            actions.append(
                AgentActionRecord(
                    action="external_search",
                    status="skipped",
                    detail="External search is disabled for this turn.",
                    payload={"candidate_count": 0},
                )
            )

        selected_documents = self._select_final_evidence(
            useful_local_documents=merged_useful_local_documents,
            external_documents=external_documents,
            external_search_attempted=external_search_attempted,
        )
        retrieval_mode = self._resolve_retrieval_mode(local_documents, external_documents, coverage)
        if library is None and not external_documents:
            retrieval_mode = "no_library"
        context = OrchestratedChatContext(
            session=session,
            library=library,
            user_message=user_message,
            retrieved_memories=memories,
            local_documents=local_documents,
            external_documents=external_documents,
            selected_documents=selected_documents,
            retrieval_mode=retrieval_mode,
            coverage=coverage,
            actions=actions,
            pending_ingest=pending_ingest,
            local_retrieval_trace=local_retrieval_trace,
            external_rerank_trace=external_rerank_trace,
        )

        yield AgentEvent(
            type="prepare_done",
            payload={"elapsed_seconds": round(time.perf_counter() - started_at, 1)},
        )
        yield AgentEvent(
            type="context_ready",
            payload=self._build_context_ready_payload(context),
            context=context,
        )

    def _assess_local_coverage_with_llm(
        self,
        *,
        user_message: str,
        local_documents: list[dict[str, Any]],
        top_k: int,
    ) -> CoverageAssessment:
        """调用 LLM 判断本地文献证据是否足够支持当前回答。"""
        unique_document_count = self._count_unique_documents(local_documents)
        rerank_scores = self._collect_rerank_scores(local_documents)
        max_rerank_score = max(rerank_scores) if rerank_scores else None
        avg_rerank_score = round(sum(rerank_scores) / len(rerank_scores), 4) if rerank_scores else None

        response = self._build_coverage_model().invoke(
            self._build_coverage_prompt(
                user_message=user_message,
                local_documents=local_documents,
                unique_document_count=unique_document_count,
                max_rerank_score=max_rerank_score,
                avg_rerank_score=avg_rerank_score,
                top_k=top_k,
            )
        )
        payload = self._parse_json_object(self._extract_model_text(response))
        return self._coverage_from_llm_payload(
            payload,
            local_unique_documents=unique_document_count,
            max_rerank_score=max_rerank_score,
            avg_rerank_score=avg_rerank_score,
            top_k=top_k,
        )

    def _build_local_only_coverage(self, local_documents: list[dict[str, Any]]) -> CoverageAssessment:
        """在未启用联网搜索时记录本地检索状态，不调用 LLM 做充分性判断。"""
        unique_document_count = self._count_unique_documents(local_documents)
        rerank_scores = self._collect_rerank_scores(local_documents)
        has_local_evidence = bool(local_documents)
        return CoverageAssessment(
            sufficient=has_local_evidence,
            should_search_external=False,
            reason_codes=[] if has_local_evidence else ["no_local_evidence"],
            local_unique_documents=unique_document_count,
            max_rerank_score=max(rerank_scores) if rerank_scores else None,
            avg_rerank_score=round(sum(rerank_scores) / len(rerank_scores), 4) if rerank_scores else None,
            freshness_gap_detected=False,
            recommended_external_limit=0,
            rationale="未启用联网搜索，仅使用本地检索结果，并跳过 LLM 证据充分性判断。",
            evaluator="system",
        )

    def _build_coverage_prompt(
        self,
        *,
        user_message: str,
        local_documents: list[dict[str, Any]],
        unique_document_count: int,
        max_rerank_score: float | None,
        avg_rerank_score: float | None,
        top_k: int,
    ) -> str:
        """构造用于证据充分性判断的 LLM 提示词。"""
        document_context = self._format_documents_for_coverage(local_documents)
        return f"""
你是论文助手中的“证据充分性评估器”。请只判断当前本地文献库证据是否足以回答用户问题，不要回答用户问题。

用户问题：
{user_message}

本地检索配置与统计：
- 最终候选 chunk 数：{len(local_documents)}
- 去重文献数：{unique_document_count}
- 期望回答使用的候选数 top_k：{top_k}
- 最高重排分：{max_rerank_score if max_rerank_score is not None else "无"}
- 平均重排分：{avg_rerank_score if avg_rerank_score is not None else "无"}

本地候选文献证据：
{document_context}

请按以下标准判断：
1. 如果本地候选证据能覆盖用户问题的核心主题、对象、时间范围、方法或对比维度，则 sufficient 为 true。
2. 如果问题要求“最新、近年、最近几年、current/latest/recent”等时效信息，而本地候选没有相应年份或覆盖不足，则 sufficient 为 false，并把 freshness_gap_detected 设为 true。
3. 如果本地候选只命中部分关键词、摘要和片段不能支撑结论、候选为空，或需要更多外部论文补充，则 sufficient 为 false。
4. 如果 sufficient 为 false，通常应把 should_search_external 设为 true，并给出 1 到 4 个简短 reason_codes。
5. recommended_external_limit 只在需要外部检索时填写，建议 10 到 20；不需要外部检索时填写 0。
6. 请同时判断每个本地候选 chunk 是否对回答有直接帮助。useful_local_evidence_ids 只填写有用候选的 evidence_id，discarded_local_evidence_ids 填写明显无关、泛泛而谈或不能支撑回答的 evidence_id。

只输出一个 JSON 对象，不要输出 Markdown 或解释。字段必须为：
{{
  "sufficient": true,
  "should_search_external": false,
  "reason_codes": ["coverage_gap"],
  "freshness_gap_detected": false,
  "recommended_external_limit": 0,
  "useful_local_evidence_ids": ["doc_1#chunk_0"],
  "discarded_local_evidence_ids": ["doc_2#chunk_3"],
  "rationale": "一句中文说明"
}}
""".strip()

    def _format_documents_for_coverage(self, documents: list[dict[str, Any]], max_items: int = config.MAX_SEARCH_NUM) -> str:
        """把候选文献压缩成适合 LLM 判断证据覆盖度的文本。"""
        if not documents:
            return "无本地候选文献。"

        lines: list[str] = []
        for index, item in enumerate(documents[:max_items], start=1):
            authors = ", ".join(str(author) for author in item.get("authors", []) if str(author).strip())
            lines.append(
                f"{index}. evidence_id={self._build_local_evidence_id(item)}\n"
                f"   source_id={item.get('source_id') or item.get('document_id') or 'unknown'}\n"
                f"   标题：{item.get('title') or '未知'}\n"
                f"   作者：{authors or '未知'}\n"
                f"   年份：{item.get('year') or '未知'}\n"
                f"   来源：{item.get('venue') or '未知'}\n"
                f"   重排分：{item.get('rerank_score') if item.get('rerank_score') is not None else '无'}\n"
                f"   摘要：{self._truncate_text(str(item.get('abstract') or ''), 500)}\n"
                f"   证据片段：{self._truncate_text(str(item.get('chunk_text') or ''), 700)}"
            )
        return "\n".join(lines)

    def _coverage_from_llm_payload(
        self,
        payload: dict[str, Any],
        *,
        local_unique_documents: int,
        max_rerank_score: float | None,
        avg_rerank_score: float | None,
        top_k: int,
    ) -> CoverageAssessment:
        """把 LLM 返回的 JSON 规范化为 CoverageAssessment。"""
        sufficient = self._as_bool(payload.get("sufficient"), default=False)
        should_search_external = False if sufficient else True
        reason_codes = self._normalize_reason_codes(payload.get("reason_codes"))
        if not sufficient and not reason_codes:
            reason_codes = ["llm_judged_insufficient"]

        recommended_limit = 0
        if should_search_external:
            recommended_limit = self._normalize_external_limit(
                payload.get("recommended_external_limit"),
                default=max(top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT),
            )
        useful_evidence_ids = self._normalize_local_evidence_ids(
            payload.get("useful_local_evidence_ids") or payload.get("useful_local_source_ids")
        )
        discarded_evidence_ids = self._normalize_local_evidence_ids(
            payload.get("discarded_local_evidence_ids") or payload.get("discarded_local_source_ids")
        )

        return CoverageAssessment(
            sufficient=sufficient,
            should_search_external=should_search_external,
            reason_codes=reason_codes,
            local_unique_documents=local_unique_documents,
            max_rerank_score=max_rerank_score,
            avg_rerank_score=avg_rerank_score,
            freshness_gap_detected=self._as_bool(payload.get("freshness_gap_detected"), default=False),
            recommended_external_limit=recommended_limit,
            useful_local_evidence_ids=useful_evidence_ids,
            discarded_local_evidence_ids=discarded_evidence_ids,
            rationale=str(payload.get("rationale") or "").strip(),
            evaluator="llm",
        )

    def _build_coverage_fallback(
        self,
        *,
        local_documents: list[dict[str, Any]],
        local_unique_documents: int,
        max_rerank_score: float | None,
        avg_rerank_score: float | None,
        error_message: str,
    ) -> CoverageAssessment:
        """在 LLM 判断失败时返回保守兜底结果，避免主聊天链路中断。"""
        has_local_evidence = bool(local_documents)
        reason_codes = ["llm_coverage_assessment_failed"]
        if not has_local_evidence:
            reason_codes.append("no_local_evidence")

        return CoverageAssessment(
            sufficient=has_local_evidence,
            should_search_external=not has_local_evidence,
            reason_codes=reason_codes,
            local_unique_documents=local_unique_documents,
            max_rerank_score=max_rerank_score,
            avg_rerank_score=avg_rerank_score,
            freshness_gap_detected=False,
            recommended_external_limit=config.DEFAULT_EXTERNAL_FINAL_LIMIT if not has_local_evidence else 0,
            rationale=f"LLM 证据充分性判断失败，已使用兜底结果：{error_message}",
            evaluator="fallback",
        )

    def _build_coverage_model(self) -> ChatTongyi:
        """根据当前全局配置创建用于证据充分性判断的模型实例。"""
        if self.config_service is None:
            raise ValueError("模型配置服务未初始化，请先完成模型配置。")
        model_name = self.config_service.get_llm_model_name()
        api_key = self.config_service.get_api_key()

        return ChatTongyi(
            model=model_name,
            api_key=api_key or None,
            streaming=False,
        )

    def _extract_model_text(self, response: Any) -> str:
        """从模型响应对象中提取文本内容。"""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "".join(parts)
        return str(content) if content else ""

    def _parse_json_object(self, raw_text: str) -> dict[str, Any]:
        """从模型输出中解析第一个 JSON 对象。"""
        normalized = (raw_text or "").strip()
        try:
            payload = json.loads(normalized)
        except json.JSONDecodeError:
            match = _JSON_OBJECT_PATTERN.search(normalized)
            if not match:
                raise ValueError("LLM 证据评估没有返回 JSON 对象。")
            payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("LLM 证据评估返回的 JSON 不是对象。")
        return payload

    def _collect_rerank_scores(self, documents: list[dict[str, Any]]) -> list[float]:
        """提取本地候选中的重排分，供 LLM 判断和调试记录使用。"""
        scores: list[float] = []
        for item in documents:
            value = item.get("rerank_score")
            if value is None:
                continue
            try:
                scores.append(float(value))
            except (TypeError, ValueError):
                continue
        return scores

    def _as_bool(self, value: Any, *, default: bool) -> bool:
        """把模型返回的布尔字段安全转换为 bool。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "1", "是", "需要"}:
                return True
            if normalized in {"false", "no", "0", "否", "不需要"}:
                return False
        return default

    def _normalize_reason_codes(self, value: Any) -> list[str]:
        """规范化 LLM 返回的原因代码列表。"""
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = value
        else:
            candidates = []

        reason_codes: list[str] = []
        for item in candidates:
            code = re.sub(r"[^a-zA-Z0-9_ -]+", "", str(item).strip().lower())
            code = re.sub(r"[\s-]+", "_", code).strip("_")
            if code and code not in reason_codes:
                reason_codes.append(code)
            if len(reason_codes) >= 4:
                break
        return reason_codes

    def _normalize_local_evidence_ids(self, value: Any) -> list[str]:
        """规范化 LLM 返回的本地候选 evidence_id 列表。"""
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = value
        else:
            candidates = []

        evidence_ids: list[str] = []
        for item in candidates:
            evidence_id = str(item or "").strip()
            if evidence_id and evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
        return evidence_ids

    def _normalize_external_limit(self, value: Any, *, default: int) -> int:
        """规范化 LLM 建议的外部检索数量。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = int(default)
        return max(1, min(parsed, config.DEFAULT_EXTERNAL_FINAL_LIMIT))

    def _truncate_text(self, value: str, max_chars: int) -> str:
        """截断长文本，控制证据评估提示词长度。"""
        normalized = re.sub(r"\s+", " ", (value or "").strip())
        if len(normalized) <= max_chars:
            return normalized or "无"
        return normalized[:max_chars].rstrip() + "..."

    def decide_ingest_candidates(
        self,
        *,
        library_id: int,
        external_candidates: list[ExternalPaperCandidate],
        user_message: str,
    ) -> list[PendingIngestRecord]:
        """根据外部候选文献生成入库决策。"""
        decisions: list[PendingIngestRecord] = []
        for candidate in external_candidates:
            decision = "queue_ingest" if candidate.pdf_url else "answer_only"
            reason = (
                "Candidate includes a downloadable PDF and is eligible for future ingest."
                if candidate.pdf_url
                else "External search candidate is available for answer augmentation only."
            )
            decisions.append(
                PendingIngestRecord(
                    external_id=candidate.external_id,
                    title=candidate.title,
                    library_id=library_id,
                    decision=decision,
                    reason=reason,
                )
            )
        return decisions

    def queue_ingest_candidates(
        self,
        *,
        library_id: int,
        candidates: list[ExternalPaperCandidate],
    ) -> list[PendingIngestRecord]:
        """把外部候选转换为待入库记录，后续可在这里创建真实后台 job。"""
        return [
            PendingIngestRecord(
                external_id=candidate.external_id,
                title=candidate.title,
                library_id=library_id,
                decision="queue_ingest",
                reason="Queueing external ingest is not wired yet.",
            )
            for candidate in candidates
        ]

    def _build_external_only_actions(self, library_id: int, top_k: int) -> list[AgentActionRecord]:
        """构造仅外部检索模式下的初始动作记录。"""
        coverage = CoverageAssessment(
            sufficient=False,
            should_search_external=True,
            reason_codes=["external_search_requested"],
            recommended_external_limit=max(top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT),
            rationale="当前请求指定只进行外部检索，跳过本地证据充分性判断。",
            evaluator="system",
        )
        return [
            AgentActionRecord(
                action="local_search",
                status="skipped",
                detail="Skipped local library retrieval because external search mode is enabled.",
                payload={"library_id": library_id},
            ),
            AgentActionRecord(
                action="coverage_assessment",
                status="skipped",
                detail="Skipped local coverage assessment because external search mode is enabled.",
                payload=asdict(coverage),
            ),
        ]

    def _build_no_library_actions(
        self,
        top_k: int,
        *,
        allow_external_search: bool = False,
    ) -> list[AgentActionRecord]:
        """构造无文献库会话下的初始动作记录。"""
        coverage = CoverageAssessment(
            sufficient=not allow_external_search,
            should_search_external=allow_external_search,
            reason_codes=["no_library_bound"] if allow_external_search else [],
            recommended_external_limit=max(top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT) if allow_external_search else 0,
            rationale="会话未绑定文献库，因此跳过本地证据充分性判断。"
            + ("启用联网搜索后将直接检索外部来源。" if allow_external_search else ""),
            evaluator="system",
        )
        return [
            AgentActionRecord(
                action="local_search",
                status="skipped",
                detail="Skipped local library retrieval because this session is not bound to a library.",
                payload={"library_id": None},
            ),
            AgentActionRecord(
                action="coverage_assessment",
                status="skipped",
                detail="Skipped local coverage assessment because this session is not bound to a library.",
                payload=asdict(coverage),
            ),
        ]

    def _build_context_ready_payload(self, context: OrchestratedChatContext) -> dict[str, Any]:
        """构造上下文准备完成事件的前端可序列化载荷。"""
        return {
            "session_id": context.session.id,
            "library_id": context.library.id if context.library else None,
            "retrieval_mode": context.retrieval_mode,
            "coverage": asdict(context.coverage),
            "agent_actions": [asdict(item) for item in context.actions],
            "pending_ingest": [asdict(item) for item in context.pending_ingest],
        }

    def _build_prepare_step_from_search_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """把外部检索服务事件转换为前端准备区步骤。"""
        event_type = str(event.get("type") or "")
        status = "running"
        if event_type == "search_query_done":
            status = "success"
        elif event_type == "search_query_error":
            status = "error"

        return {
            "id": str(event.get("query_id") or event.get("query") or "external-query"),
            "status": status,
            "source": str(event.get("source") or "arxiv"),
            "query": str(event.get("query") or ""),
            "sort_by": str(event.get("sort_by") or "relevance"),
            "sort_order": str(event.get("sort_order") or "descending"),
            "request_url": str(event.get("request_url") or ""),
            "result_count": event.get("result_count"),
            "source_total": event.get("source_total"),
            "source_completed": event.get("source_completed"),
            "source_remaining": event.get("source_remaining"),
            "source_result_count": event.get("source_result_count"),
            "source_error_count": event.get("source_error_count"),
            "error": str(event.get("error") or ""),
            "error_kind": str(event.get("error_kind") or ""),
        }

    def _build_library_prepare_step(self, library_name: str, status: str, result_count: int) -> dict[str, Any]:
        """构造本地文献库检索的准备区步骤。"""
        return {
            "id": "local-library-search",
            "status": status,
            "source": "library",
            "query": library_name,
            "sort_by": "local",
            "sort_order": "",
            "result_count": result_count,
            "error": "",
        }

    def _build_coverage_prepare_step(
        self,
        status: str,
        *,
        coverage: CoverageAssessment | None = None,
        error: str = "",
    ) -> dict[str, Any]:
        """构造证据充分性判断的准备区步骤，用于 trace 记录真实 LLM 调用耗时。"""
        return {
            "id": "coverage-assessment",
            "status": status,
            "source": "coverage",
            "query": "",
            "sort_by": "",
            "sort_order": "",
            "result_count": None,
            "coverage_sufficient": coverage.sufficient if coverage is not None else None,
            "coverage_rationale": coverage.rationale if coverage is not None else "",
            "error": error,
        }

    def _build_search_plan_prepare_step(
        self,
        status: str,
        *,
        search_plan: ExternalSearchPlan | None = None,
        error: str = "",
    ) -> dict[str, Any]:
        """构造外部检索计划生成步骤，用于准备区展示和 trace 记录 LLM 规划耗时。"""
        return {
            "id": "external-search-plan",
            "status": status,
            "source": "search_plan",
            "query": "",
            "sort_by": "",
            "sort_order": "",
            "result_count": len(search_plan.queries) if search_plan is not None else None,
            "search_plan_text": self._format_search_plan_for_display(search_plan) if search_plan is not None else "",
            "search_plan": search_plan.to_dict() if search_plan is not None else None,
            "planned_by_model": search_plan.planned_by_model if search_plan is not None else None,
            "error": error,
        }

    def _format_search_plan_for_display(self, search_plan: ExternalSearchPlan | None) -> str:
        """把 LLM 返回的检索计划压缩成准备区可读的多行文本。"""
        if search_plan is None or not search_plan.queries:
            return "暂无检索计划"

        parts: list[str] = []
        for index, query_plan in enumerate(search_plan.queries, start=1):
            keywords = " + ".join(query_plan.query) if query_plan.query else "未命名查询"
            sources = ", ".join(query_plan.sources or ["arxiv", "openalex"])
            date_text = f"，date_from={query_plan.date_from}" if query_plan.date_from else ""
            parts.append(
                f"{index}. [{sources}] {keywords}{date_text}，"
                f"sort={query_plan.sortby}/{query_plan.orderby}，limit={query_plan.limit}"
            )
        return "\n".join(parts)

    def _count_unique_documents(self, documents: list[dict[str, Any]]) -> int:
        """统计检索结果中去重后的文献数量。"""
        document_ids = {
            item.get("document_id")
            for item in documents
            if item.get("document_id") is not None
        }
        if document_ids:
            return len(document_ids)
        source_ids = {
            item.get("source_id")
            for item in documents
            if item.get("source_id")
        }
        return len(source_ids)

    def _search_local_documents_with_trace(
        self,
        *,
        user_message: str,
        library_id: int,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """调用本地 hybrid retriever，并返回最终结果和可观测 trace 数据。"""
        search_result = self.retriever_service.search_with_trace(
            user_message,
            library_id=library_id,
            top_k=top_k,
            recall_k=self._get_recall_chunks(),
        )
        documents = [self._attach_source_id(document) for document in search_result.get("documents", [])]
        trace = self._attach_source_ids_to_local_trace(search_result.get("trace") or {})
        return documents, trace

    def _attach_source_ids_to_local_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        """为本地检索各阶段 trace 文档补充稳定 source_id，便于前端详情展示。"""
        normalized_trace: dict[str, Any] = {}
        for key, value in trace.items():
            if not isinstance(value, dict):
                continue
            documents = value.get("documents")
            normalized_trace[key] = {
                **value,
                "documents": [
                    self._attach_source_id(document)
                    for document in documents
                    if isinstance(document, dict)
                ]
                if isinstance(documents, list)
                else [],
            }
        return normalized_trace

    def _build_external_search_plan(
        self,
        query: str,
        *,
        limit: int,
        freshness_requested: bool = False,
    ) -> ExternalSearchPlan:
        """构造外部检索计划；有 planner 时优先让模型提取 MCP 参数。"""
        if self.external_search_planner_service is None:
            raise RuntimeError("外部检索计划服务未初始化，无法生成检索计划。")

        return self.external_search_planner_service.plan(
            query,
            default_limit=limit,
            freshness_requested=freshness_requested,
        )

    def _build_fallback_external_keywords(self, query: str) -> list[str]:
        """在没有外部检索规划器时，从用户问题中提取保守的通用关键词列表。"""
        normalized = re.sub(r"\s+", " ", (query or "").strip())
        if not normalized:
            return ["paper"]

        keywords: list[str] = []
        quoted_phrases = re.findall(r'["“”‘’\']([^"“”‘’\']{2,80})["“”‘’\']', normalized)
        for phrase in quoted_phrases:
            keyword = re.sub(r"\s+", " ", phrase.strip())
            if keyword and keyword not in keywords:
                keywords.append(keyword)

        english_terms = re.findall(r"[A-Za-z][A-Za-z0-9 -]{1,48}", normalized)
        for term in english_terms:
            keyword = re.sub(r"\s+", " ", term.strip())
            if keyword and keyword.lower() not in {"and", "or", "the", "for"} and keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 4:
                break

        return keywords[:4] or [normalized[:80]]

    def _prepare_external_documents(
        self,
        local_documents: list[dict[str, Any]],
        external_candidates: list[ExternalPaperCandidate],
    ) -> list[dict[str, Any]]:
        """把外部候选转换为与本地检索结果兼容的证据结构。"""
        local_dois = {self._normalize_text(item.get("doi") or "") for item in local_documents if item.get("doi")}
        local_titles = {self._normalize_text(item.get("title") or "") for item in local_documents if item.get("title")}
        prepared: list[dict[str, Any]] = []

        for index, candidate in enumerate(external_candidates):
            normalized_title = self._normalize_text(candidate.title)
            normalized_doi = self._normalize_text(candidate.doi)
            if (normalized_doi and normalized_doi in local_dois) or (normalized_title and normalized_title in local_titles):
                continue
            prepared.append(
                {
                    "library_id": None,
                    "document_id": None,
                    "title": candidate.title,
                    "authors": candidate.authors,
                    "year": candidate.year,
                    "venue": candidate.venue,
                    "abstract": candidate.abstract,
                    "doi": candidate.doi,
                    "url": candidate.url,
                    "citation_text_default": candidate.citation_text_default or candidate.title,
                    "publisher": candidate.publisher,
                    "publisher_place": candidate.publisher_place,
                    "volume": candidate.volume,
                    "issue": candidate.issue,
                    "pages": candidate.pages,
                    "article_number": candidate.article_number,
                    "degree_institution": candidate.degree_institution,
                    "degree_location": candidate.degree_location,
                    "proceedings_title": candidate.proceedings_title,
                    "conference_name": candidate.conference_name,
                    "publication_date": candidate.publication_date,
                    "document_type": candidate.document_type,
                    "metadata_sources": candidate.metadata_sources or [candidate.source],
                    "file_path": "",
                    "chunk_index": index,
                    "chunk_text": candidate.abstract,
                    "recall_rank": index,
                    "rerank_score": candidate.relevance_score or 0.0,
                    "source_id": f"ext_{candidate.source}_{candidate.external_id}",
                    "source_type": "external",
                    "matched_query": candidate.matched_query,
                }
            )
        return prepared

    def _rerank_external_documents_with_trace(
        self,
        user_message: str,
        external_documents: list[dict[str, Any]],
        *,
        external_quota: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """对不同外部数据源返回的候选统一重排，并返回 trace 诊断数据。"""
        if not external_documents:
            return [], {}

        normalized_quota = max(0, min(int(external_quota), config.MAX_SEARCH_NUM))
        if normalized_quota <= 0:
            return [], self._build_skipped_external_rerank_trace(
                external_documents=external_documents,
                external_quota=normalized_quota,
                selected_documents=[],
                reason="本地有用证据已占满最终上下文额度，跳过外部重排。",
            )

        if len(external_documents) <= normalized_quota:
            selected_documents = external_documents[:normalized_quota]
            return selected_documents, self._build_skipped_external_rerank_trace(
                external_documents=external_documents,
                external_quota=normalized_quota,
                selected_documents=selected_documents,
                reason="外部候选数未超过最终上下文可用额度，跳过外部重排。",
            )

        rerank_candidates = external_documents[: config.RERANK_MAX_DOCUMENTS]
        started_at = time.perf_counter()
        reranked_documents = self.retriever_service.rerank_service.rerank_external_papers(
            query=user_message,
            candidates=rerank_candidates,
            top_k=normalized_quota,
        )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        trace = {
            "elapsed_ms": elapsed_ms,
            "candidate_count": len(rerank_candidates),
            "result_count": len(reranked_documents),
            "top_k": normalized_quota,
            "external_quota": normalized_quota,
            "skipped": False,
            "skip_reason": "",
            **self._build_external_rerank_trace_metadata(reranked_documents),
            "documents": reranked_documents,
        }
        return reranked_documents, trace

    def _build_skipped_external_rerank_trace(
        self,
        *,
        external_documents: list[dict[str, Any]],
        external_quota: int,
        selected_documents: list[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """构造跳过外部重排时的 trace 数据，方便前端保留可观测记录。"""
        return {
            "elapsed_ms": 0,
            "candidate_count": len(external_documents),
            "result_count": len(selected_documents),
            "top_k": external_quota,
            "external_quota": external_quota,
            "provider": "",
            "fallback_used": False,
            "fallback_error": "",
            "skipped": True,
            "skip_reason": reason,
            "documents": selected_documents,
        }

    def _build_external_rerank_trace_metadata(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """从外部重排结果中提取 trace 可展示的来源信息。"""
        if not documents:
            return {
                "provider": "unknown",
                "fallback_used": False,
                "fallback_error": "",
            }
        first = documents[0]
        return {
            "provider": first.get("rerank_provider") or "unknown",
            "fallback_used": bool(first.get("rerank_fallback_used")),
            "fallback_error": str(first.get("rerank_error") or ""),
        }

    def _select_final_evidence(
        self,
        *,
        useful_local_documents: list[dict[str, Any]],
        external_documents: list[dict[str, Any]],
        external_search_attempted: bool,
    ) -> list[dict[str, Any]]:
        """从本地与外部证据中选出最终送入提示词的结果。"""
        if not external_documents:
            return useful_local_documents[: config.MAX_SEARCH_NUM]
        if not useful_local_documents:
            return external_documents[: config.MAX_SEARCH_NUM]

        local_limited = useful_local_documents[: config.MAX_SEARCH_NUM]
        external_limit = max(0, config.MAX_SEARCH_NUM - len(local_limited))
        external_limited = external_documents[:external_limit]
        # 不混排本地重排分和外部重排分；先保留 LLM 判定有用的本地证据，再用外部证据补足上下文。
        return [*local_limited, *external_limited][: config.MAX_SEARCH_NUM]

    def _merge_adjacent_useful_local_chunks(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把同一篇文献中相邻的有用 chunk 合并为一个最终证据块。"""
        if not documents:
            return []

        grouped_documents: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for order, document in enumerate(documents):
            if str(document.get("source_type") or "local").lower() == "external":
                continue
            group_key = self._build_local_document_group_key(document, order)
            grouped_documents.setdefault(group_key, []).append((order, document))

        merged_documents: list[tuple[int, dict[str, Any]]] = []
        for items in grouped_documents.values():
            ordered_items = sorted(
                items,
                key=lambda item: (
                    self._chunk_sort_key(item[1].get("chunk_index")),
                    item[0],
                ),
            )
            current_run: list[tuple[int, dict[str, Any]]] = []
            previous_chunk_index: int | None = None
            for item in ordered_items:
                chunk_index = self._coerce_chunk_index(item[1].get("chunk_index"))
                if (
                    current_run
                    and chunk_index is not None
                    and previous_chunk_index is not None
                    and chunk_index == previous_chunk_index + 1
                ):
                    current_run.append(item)
                else:
                    if current_run:
                        merged_documents.append(self._merge_local_chunk_run(current_run))
                    current_run = [item]
                previous_chunk_index = chunk_index
            if current_run:
                merged_documents.append(self._merge_local_chunk_run(current_run))

        merged_documents.sort(key=lambda item: item[0])
        return [document for _, document in merged_documents]

    def _build_local_document_group_key(self, document: dict[str, Any], fallback_order: int) -> str:
        """构造本地文献合并分组键，优先按 document_id 合并。"""
        document_id = document.get("document_id")
        if document_id is not None:
            return f"document:{document_id}"
        source_id = str(document.get("source_id") or "").strip()
        if source_id:
            return f"source:{source_id}"
        file_path = str(document.get("file_path") or "").strip()
        if file_path:
            return f"file:{file_path}"
        return f"fallback:{fallback_order}"

    def _merge_local_chunk_run(self, run_items: list[tuple[int, dict[str, Any]]]) -> tuple[int, dict[str, Any]]:
        """合并一组同文献且 chunk_index 连续的候选分块。"""
        ordered_documents = [dict(document) for _, document in run_items]
        first_order = min(order for order, _ in run_items)
        if len(ordered_documents) == 1:
            return first_order, ordered_documents[0]

        merged_document = dict(ordered_documents[0])
        chunk_indexes = [document.get("chunk_index") for document in ordered_documents]
        merged_document["chunk_index"] = chunk_indexes[0]
        merged_document["chunk_end_index"] = chunk_indexes[-1]
        merged_document["merged_chunk_indexes"] = chunk_indexes
        merged_document["merged_chunks"] = ordered_documents
        merged_document["chunk_text"] = "\n\n".join(
            str(document.get("chunk_text") or "").strip()
            for document in ordered_documents
            if str(document.get("chunk_text") or "").strip()
        )
        merged_document["rerank_score"] = self._max_numeric_field(ordered_documents, "rerank_score")
        merged_document["qwen_rerank_score"] = self._max_numeric_field(ordered_documents, "qwen_rerank_score")
        merged_document["keyword_score"] = self._max_numeric_field(ordered_documents, "keyword_score")
        merged_document["hybrid_score"] = self._max_numeric_field(ordered_documents, "hybrid_score")
        merged_document["vector_rank"] = self._min_numeric_field(ordered_documents, "vector_rank")
        merged_document["keyword_rank"] = self._min_numeric_field(ordered_documents, "keyword_rank")
        merged_document["hybrid_rank"] = self._min_numeric_field(ordered_documents, "hybrid_rank")
        return first_order, merged_document

    def _coerce_chunk_index(self, value: Any) -> int | None:
        """把 chunk_index 规范化为整数，无法解析时返回 None。"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _chunk_sort_key(self, value: Any) -> int:
        """生成可排序的 chunk_index 键，缺失值排在最后。"""
        chunk_index = self._coerce_chunk_index(value)
        return chunk_index if chunk_index is not None else 10**9

    def _max_numeric_field(self, documents: list[dict[str, Any]], field_name: str) -> Any:
        """读取一组分块中指定数值字段的最大值，保留原始空值语义。"""
        values = [self._coerce_float(document.get(field_name)) for document in documents]
        numeric_values = [value for value in values if value is not None]
        return max(numeric_values) if numeric_values else documents[0].get(field_name)

    def _min_numeric_field(self, documents: list[dict[str, Any]], field_name: str) -> Any:
        """读取一组分块中指定排名字段的最小值，排名越小表示越靠前。"""
        values = [self._coerce_float(document.get(field_name)) for document in documents]
        numeric_values = [value for value in values if value is not None]
        if not numeric_values:
            return documents[0].get(field_name)
        minimum = min(numeric_values)
        return int(minimum) if float(minimum).is_integer() else minimum

    def _coerce_float(self, value: Any) -> float | None:
        """把可能来自 trace 的数值字段转换为 float。"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _calculate_external_evidence_quota(self, useful_local_documents: list[dict[str, Any]]) -> int:
        """根据有用本地证据数量计算外部文献在最终上下文中的可用额度。"""
        local_count = min(len(useful_local_documents), config.MAX_SEARCH_NUM)
        return max(0, config.MAX_SEARCH_NUM - local_count)

    def _filter_useful_local_documents(
        self,
        local_documents: list[dict[str, Any]],
        coverage: CoverageAssessment,
    ) -> list[dict[str, Any]]:
        """根据充分性判断结果过滤明显无用的本地候选 chunk。"""
        if not local_documents:
            return []

        useful_ids = set(coverage.useful_local_evidence_ids)
        discarded_ids = set(coverage.discarded_local_evidence_ids)
        if useful_ids:
            filtered = [
                document
                for document in local_documents
                if self._local_document_matches_evidence_ids(document, useful_ids)
            ]
            if filtered:
                return filtered

        if discarded_ids:
            return [
                document
                for document in local_documents
                if not self._local_document_matches_evidence_ids(document, discarded_ids)
            ]

        return local_documents

    def _local_document_matches_evidence_ids(self, document: dict[str, Any], evidence_ids: set[str]) -> bool:
        """判断本地候选是否命中 LLM 标记的 evidence_id，兼容文献级 source_id。"""
        source_id = str(document.get("source_id") or "").strip()
        evidence_id = self._build_local_evidence_id(document)
        return evidence_id in evidence_ids or (source_id and source_id in evidence_ids)

    def _build_local_evidence_id(self, document: dict[str, Any]) -> str:
        """为本地候选 chunk 构造稳定 evidence_id，供充分性判断按分块过滤。"""
        source_id = str(document.get("source_id") or "").strip()
        if not source_id and document.get("document_id") is not None:
            source_id = self._build_source_id(int(document["document_id"]))
        source_id = source_id or "unknown_source"
        chunk_index = document.get("chunk_index")
        chunk_text = chunk_index if chunk_index is not None else "unknown"
        return f"{source_id}#chunk_{chunk_text}"

    def _resolve_retrieval_mode(
        self,
        local_documents: list[dict[str, Any]],
        external_documents: list[dict[str, Any]],
        coverage: CoverageAssessment,
    ) -> str:
        """根据证据来源判断当前问答属于哪种检索模式。"""
        if not coverage.should_search_external:
            return "local_only"
        if local_documents and external_documents:
            return "hybrid"
        if external_documents:
            return "external_augmented"
        return "local_only"

    def _attach_source_id(self, document: dict[str, Any]) -> dict[str, Any]:
        """给本地检索结果补充稳定的 source_id。"""
        payload = dict(document)
        if payload.get("document_id") is not None:
            payload["source_id"] = self._build_source_id(int(payload["document_id"]))
        return payload

    def _build_source_id(self, document_id: int) -> str:
        """为本地文献构造统一的引用标识。"""
        return f"doc_{document_id}"

    def _get_recall_chunks(self) -> int:
        """读取当前配置中的召回候选数。"""
        return config.TOP_K

    def _get_rerank_chunks(self) -> int:
        """读取当前配置中的最终重排保留数。"""
        return config.RECALL_K

    def _require_session(self, session_id: int) -> SessionRecord:
        """按会话 ID 获取会话，不存在时抛出明确异常。"""
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return session

    def _require_library(self, library_id: int) -> LibraryRecord:
        """按文献库 ID 获取文献库，不存在时抛出明确异常。"""
        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")
        return library

    def _get_optional_library(self, library_id: int | None) -> LibraryRecord | None:
        """按需获取文献库；无绑定时返回 None。"""
        if library_id is None:
            return None
        return self._require_library(library_id)

    def _normalize_text(self, value: str) -> str:
        """对标题、DOI 等文本做归一化，便于去重比较。"""
        return (value or "").strip().lower()
