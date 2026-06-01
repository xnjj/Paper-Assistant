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
    ExternalSearchQueryPlan,
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
        top_k: int = 5,
        external_search_only: bool = False,
        allow_external_search: bool = False,
    ) -> Iterator[AgentEvent]:
        """以事件形式输出上下文准备进度，并在最后返回完整上下文。"""
        started_at = time.perf_counter()
        yield AgentEvent(type="prepare_start", payload={})

        session = self._require_session(session_id)
        library = self._get_optional_library(session.library_id)
        memories = self.memory_service.recall_memories(user_message, session_id=session_id, limit=5)
        # 本地召回/重排数量统一由 config_data.py 固定，忽略前端传入的 top_k，便于测试和复现。
        effective_top_k = self._get_rerank_chunks()

        if library is None:
            local_documents = []
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
            local_documents = self._search_local_documents(
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
                        "chunk_limit_per_paper": config.CHUNK_LIMIT_PER_PAPER,
                    },
                )
            ]
            if allow_external_search:
                coverage = self._assess_local_coverage_with_llm(
                    user_message=user_message,
                    local_documents=local_documents,
                    top_k=effective_top_k,
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
        pending_ingest: list[PendingIngestRecord] = []

        if allow_external_search and coverage.should_search_external:
            search_plan = self._build_external_search_plan(
                user_message,
                limit=coverage.recommended_external_limit or max(effective_top_k, config.DEFAULT_EXTERNAL_FINAL_LIMIT),
                freshness_requested=coverage.freshness_gap_detected,
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
            local_documents=local_documents,
            external_documents=external_documents,
            top_k=effective_top_k,
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

        try:
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
        except Exception as exc:
            return self._build_coverage_fallback(
                local_documents=local_documents,
                local_unique_documents=unique_document_count,
                max_rerank_score=max_rerank_score,
                avg_rerank_score=avg_rerank_score,
                error_message=str(exc),
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

只输出一个 JSON 对象，不要输出 Markdown 或解释。字段必须为：
{{
  "sufficient": true,
  "should_search_external": false,
  "reason_codes": ["coverage_gap"],
  "freshness_gap_detected": false,
  "recommended_external_limit": 0,
  "rationale": "一句中文说明"
}}
""".strip()

    def _format_documents_for_coverage(self, documents: list[dict[str, Any]], max_items: int = 8) -> str:
        """把候选文献压缩成适合 LLM 判断证据覆盖度的文本。"""
        if not documents:
            return "无本地候选文献。"

        lines: list[str] = []
        for index, item in enumerate(documents[:max_items], start=1):
            authors = ", ".join(str(author) for author in item.get("authors", []) if str(author).strip())
            lines.append(
                f"{index}. source_id={item.get('source_id') or item.get('document_id') or 'unknown'}\n"
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

        return CoverageAssessment(
            sufficient=sufficient,
            should_search_external=should_search_external,
            reason_codes=reason_codes,
            local_unique_documents=local_unique_documents,
            max_rerank_score=max_rerank_score,
            avg_rerank_score=avg_rerank_score,
            freshness_gap_detected=self._as_bool(payload.get("freshness_gap_detected"), default=False),
            recommended_external_limit=recommended_limit,
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
        model_name = config.LLM_MODEL_NAME
        api_key = config.OPENAI_API_KEY
        if self.config_service is not None:
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
            "result_count": event.get("result_count"),
            "error": str(event.get("error") or ""),
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

    def _search_local_documents(self, *, user_message: str, library_id: int, top_k: int) -> list[dict[str, Any]]:
        """调用本地 retriever，并为结果补充稳定 source_id。"""
        return [
            self._attach_source_id(document)
            for document in self.retriever_service.search(
                user_message,
                library_id=library_id,
                top_k=top_k,
                recall_k=self._get_recall_chunks(),
            )
        ]

    def _build_external_search_plan(
        self,
        query: str,
        *,
        limit: int,
        freshness_requested: bool = False,
    ) -> ExternalSearchPlan:
        """构造外部检索计划；有 planner 时优先让模型提取 MCP 参数。"""
        if self.external_search_planner_service is not None:
            return self.external_search_planner_service.plan(
                query,
                default_limit=limit,
                freshness_requested=freshness_requested,
            )
        return ExternalSearchPlan(
            queries=[
                ExternalSearchQueryPlan(
                    query=query,
                    limit=min(max(limit, 1), config.DEFAULT_EXTERNAL_FINAL_LIMIT),
                    year_from=2024 if freshness_requested else None,
                    sort_by="submittedDate" if freshness_requested else "relevance",
                    sort_order="descending",
                    sources=["arxiv"],
                )
            ],
            final_limit=config.DEFAULT_EXTERNAL_FINAL_LIMIT,
            rationale="Fallback search plan.",
            planned_by_model=False,
        )

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

    def _select_final_evidence(
        self,
        *,
        local_documents: list[dict[str, Any]],
        external_documents: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """从本地与外部证据中选出最终送入提示词的结果。"""
        if not external_documents:
            return local_documents[: self._get_rerank_chunks()]
        if not local_documents:
            return external_documents[: config.DEFAULT_EXTERNAL_FINAL_LIMIT]

        local_limit = max(0, config.MAX_SEARCH_NUM - config.DEFAULT_EXTERNAL_FINAL_LIMIT)
        external_limited = external_documents[: config.DEFAULT_EXTERNAL_FINAL_LIMIT]
        local_limited = local_documents[:local_limit]
        # 不混排本地重排分和外部检索分，按来源固定配额拼接，避免不同评分尺度互相干扰。
        return [*local_limited, *external_limited][: config.MAX_SEARCH_NUM]

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
