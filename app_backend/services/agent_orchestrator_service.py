from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from app_backend.models import LibraryRecord, MemoryRecord, SessionRecord
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.services.config_service import ConfigService
from app_backend.services.external_search_service import (
    ExternalPaperCandidate,
    ExternalSearchService,
    NullExternalSearchService,
)
from app_backend.services.memory_service import MemoryService
from app_backend.services.retriever_service import RetrieverService


_FRESHNESS_HINT_PATTERN = re.compile(r"(最新|最近|近年|近期|current|latest|recent|202[5-9])", re.IGNORECASE)
_BREADTH_HINT_PATTERN = re.compile(r"(综述|review|survey|对比|比较|总结|实验|benchmark)", re.IGNORECASE)


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


@dataclass
class PendingIngestRecord:
    """记录外部候选文献后续是否需要进入文献库。"""

    external_id: str
    title: str
    library_id: int
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
    library: LibraryRecord
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
    ) -> None:
        """初始化编排服务，并注入本地检索与外部检索依赖。"""
        self.session_repository = session_repository
        self.library_repository = library_repository
        self.memory_service = memory_service
        self.retriever_service = retriever_service
        self.config_service = config_service
        self.external_search_service = external_search_service or NullExternalSearchService()

    def prepare_chat_context(
        self,
        session_id: int,
        user_message: str,
        top_k: int = 5,
        external_search_only: bool = False,
        allow_external_search: bool = False,
    ) -> OrchestratedChatContext:
        """为一次问答准备最终上下文。"""
        session = self._require_session(session_id)
        library = self._require_library(session.library_id)
        memories = self.memory_service.recall_memories(user_message, session_id=session_id, limit=5)
        effective_top_k = top_k if top_k > 0 else self._get_rerank_chunks()

        if external_search_only:
            local_documents: list[dict[str, Any]] = []
            actions = self._build_external_only_actions(library.id, effective_top_k)
            coverage = CoverageAssessment(
                sufficient=False,
                should_search_external=True,
                reason_codes=["external_search_requested"],
                local_unique_documents=0,
                recommended_external_limit=max(effective_top_k, 5),
            )
        else:
            local_documents = self._search_local_documents(
                user_message=user_message,
                library_id=library.id,
                top_k=effective_top_k,
            )
            actions = [
                AgentActionRecord(
                    action="local_search",
                    status="completed",
                    detail=f"Retrieved {len(local_documents)} local evidence chunks.",
                    payload={"library_id": library.id, "top_k": effective_top_k, "recall_k": self._get_recall_chunks()},
                )
            ]
            coverage = self.assess_local_coverage(
                user_message=user_message,
                local_documents=local_documents,
                top_k=effective_top_k,
            )
            actions.append(
                AgentActionRecord(
                    action="coverage_assessment",
                    status="completed",
                    detail="Assessed whether local evidence is sufficient.",
                    payload=asdict(coverage),
                )
            )

        external_documents: list[dict[str, Any]] = []
        pending_ingest: list[PendingIngestRecord] = []

        if allow_external_search and coverage.should_search_external:
            external_candidates = self._search_external_candidates(
                user_message,
                limit=coverage.recommended_external_limit or max(effective_top_k, 5),
                freshness_requested=coverage.freshness_gap_detected,
            )
            actions.append(
                AgentActionRecord(
                    action="external_search",
                    status="completed" if external_candidates else "skipped",
                    detail="Searched external sources for supplementary evidence."
                    if external_candidates
                    else "External search returned no candidates.",
                    payload={"candidate_count": len(external_candidates)},
                )
            )
            external_documents = self._prepare_external_documents(local_documents, external_candidates)
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

        return OrchestratedChatContext(
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

    def stream_prepare_chat_context(
        self,
        session_id: int,
        user_message: str,
        top_k: int = 5,
        external_search_only: bool = False,
        allow_external_search: bool = False,
    ) -> Iterator[AgentEvent]:
        """以事件形式输出上下文准备结果，当前先返回 context_ready 事件。"""
        context = self.prepare_chat_context(
            session_id=session_id,
            user_message=user_message,
            top_k=top_k,
            external_search_only=external_search_only,
            allow_external_search=allow_external_search,
        )
        yield AgentEvent(
            type="context_ready",
            payload={
                "session_id": context.session.id,
                "library_id": context.library.id,
                "retrieval_mode": context.retrieval_mode,
                "coverage": asdict(context.coverage),
                "agent_actions": [asdict(item) for item in context.actions],
                "pending_ingest": [asdict(item) for item in context.pending_ingest],
            },
        )

    def assess_local_coverage(
        self,
        *,
        user_message: str,
        local_documents: list[dict[str, Any]],
        top_k: int,
    ) -> CoverageAssessment:
        """评估本地文献证据是否足以回答当前问题。"""
        unique_document_ids = {
            int(item["document_id"])
            for item in local_documents
            if item.get("document_id") is not None
        }
        rerank_scores = [
            float(item["rerank_score"])
            for item in local_documents
            if item.get("rerank_score") is not None
        ]

        reason_codes: list[str] = []
        freshness_gap_detected = bool(_FRESHNESS_HINT_PATTERN.search(user_message))
        breadth_requested = bool(_BREADTH_HINT_PATTERN.search(user_message))

        if len(unique_document_ids) < min(max(top_k, 1), 3):
            reason_codes.append("too_few_local_docs")

        max_rerank_score = max(rerank_scores) if rerank_scores else None
        avg_rerank_score = round(sum(rerank_scores) / len(rerank_scores), 4) if rerank_scores else None

        if max_rerank_score is None or max_rerank_score < 5.0:
            reason_codes.append("low_relevance_scores")

        if freshness_gap_detected:
            reason_codes.append("freshness_requested")

        if breadth_requested and len(unique_document_ids) < max(4, top_k):
            reason_codes.append("broader_coverage_needed")

        should_search_external = bool(reason_codes)
        return CoverageAssessment(
            sufficient=not should_search_external,
            should_search_external=should_search_external,
            reason_codes=reason_codes,
            local_unique_documents=len(unique_document_ids),
            max_rerank_score=max_rerank_score,
            avg_rerank_score=avg_rerank_score,
            freshness_gap_detected=freshness_gap_detected,
            recommended_external_limit=max(top_k, 5) if should_search_external else 0,
        )

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
            recommended_external_limit=max(top_k, 5),
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

    def _search_external_candidates(
        self,
        query: str,
        *,
        limit: int,
        freshness_requested: bool = False,
    ) -> list[ExternalPaperCandidate]:
        """调用外部检索服务获取候选论文。"""
        year_from = 2024 if freshness_requested else None
        return self.external_search_service.search_papers(query, limit=limit, year_from=year_from)

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
            return local_documents

        combined = [*local_documents, *external_documents]
        combined.sort(
            key=lambda item: (
                float(item.get("rerank_score") or 0.0),
                -int(item.get("recall_rank") or 0),
            ),
            reverse=True,
        )
        return combined[: max(top_k, len(local_documents))]

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
        if self.config_service is None:
            return 20
        return self.config_service.get_recall_chunks()

    def _get_rerank_chunks(self) -> int:
        """读取当前配置中的最终重排保留数。"""
        if self.config_service is None:
            return 5
        return self.config_service.get_rerank_chunks()

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

    def _normalize_text(self, value: str) -> str:
        """对标题、DOI 等文本做归一化，便于去重比较。"""
        return (value or "").strip().lower()
