from __future__ import annotations

import json
import time
from typing import Any

import config_data as config
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.services.keyword_search_service import KeywordSearchService
from app_backend.services.rerank_service import RerankService
from app_backend.services.vector_index_service import VectorIndexService


class RetrieverService:
    """Library-aware retrieval service.

    This service combines vector recall results with structured document
    metadata so downstream chat prompts can cite titles, abstracts, and files.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        library_repository: LibraryRepository,
        vector_index_service: VectorIndexService,
        rerank_service: RerankService,
        keyword_search_service: KeywordSearchService | None = None,
    ) -> None:
        """Initialize the retrieval service.

        Args:
            document_repository: Structured document repository used for
                metadata lookups.
            library_repository: Repository used to resolve library collections.
            vector_index_service: Vector search service.
            rerank_service: Candidate reranker used after vector recall.
            keyword_search_service: Optional BM25 keyword recall service.
        """
        self.document_repository = document_repository
        self.library_repository = library_repository
        self.vector_index_service = vector_index_service
        self.rerank_service = rerank_service
        self.keyword_search_service = keyword_search_service

    def search(self, query: str, library_id: int, top_k: int = 5, recall_k: int | None = None) -> list[dict]:
        """Search the target library and return only final reranked evidence."""
        return self.search_with_trace(
            query=query,
            library_id=library_id,
            top_k=top_k,
            recall_k=recall_k,
        )["documents"]

    def search_with_trace(
        self,
        query: str,
        library_id: int,
        top_k: int = 5,
        recall_k: int | None = None,
    ) -> dict[str, Any]:
        """Search with hybrid vector/BM25 recall and return trace-friendly diagnostics."""
        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

        effective_recall_k = max(recall_k or max(top_k * 4, 20), top_k)
        keyword_recall_k = max(top_k, int(getattr(config, "KEYWORD_RECALL_K", effective_recall_k)))

        vector_started_at = time.perf_counter()
        vector_results = self.vector_index_service.search(
            collection_name=library.collection_name,
            library_id=library.id,
            query=query,
            top_k=effective_recall_k,
        )
        vector_candidates = self._build_vector_candidates(
            vector_results=vector_results,
            library_id=library_id,
        )
        vector_elapsed_ms = self._elapsed_ms(vector_started_at)

        keyword_started_at = time.perf_counter()
        keyword_candidates = (
            self.keyword_search_service.search(
                query=query,
                library_id=library_id,
                top_k=keyword_recall_k,
            )
            if self.keyword_search_service is not None
            else []
        )
        keyword_elapsed_ms = self._elapsed_ms(keyword_started_at)

        merged_results = self._merge_hybrid_candidates(
            vector_candidates=vector_candidates,
            keyword_candidates=keyword_candidates,
            max_candidates=max(top_k, int(getattr(config, "HYBRID_CANDIDATE_LIMIT", effective_recall_k))),
            rrf_k=max(1, int(getattr(config, "HYBRID_RRF_K", 60))),
        )

        rerank_started_at = time.perf_counter()
        reranked_results = self.rerank_service.rerank(
            query=query,
            candidates=merged_results,
            top_k=top_k,
        )
        rerank_elapsed_ms = self._elapsed_ms(rerank_started_at)
        return {
            "documents": reranked_results,
            "trace": {
                "vector_recall": {
                    "elapsed_ms": vector_elapsed_ms,
                    "result_count": len(vector_candidates),
                    "top_k": effective_recall_k,
                    "documents": vector_candidates,
                },
                "keyword_recall": {
                    "elapsed_ms": keyword_elapsed_ms,
                    "result_count": len(keyword_candidates),
                    "top_k": keyword_recall_k,
                    "documents": keyword_candidates,
                },
                "hybrid_rrf": {
                    "result_count": len(merged_results),
                    "rrf_k": max(1, int(getattr(config, "HYBRID_RRF_K", 60))),
                    "documents": merged_results,
                },
                "local_rerank": {
                    "elapsed_ms": rerank_elapsed_ms,
                    "result_count": len(reranked_results),
                    "top_k": top_k,
                    **self._build_rerank_trace_metadata(reranked_results),
                    "documents": reranked_results,
                },
            },
        }

    def _build_vector_candidates(self, *, vector_results: list, library_id: int) -> list[dict]:
        """把 Chroma 向量召回结果转换为统一候选结构。"""
        candidates: list[dict] = []
        for recall_rank, item in enumerate(vector_results):
            metadata = item.metadata or {}
            document_id = metadata.get("document_id")
            if document_id is None:
                continue

            document = self.document_repository.get_by_id(int(document_id))
            if document is None or document.library_id != library_id:
                continue

            authors = self._loads_json_list(document.authors_json)
            candidates.append(
                {
                    "library_id": library_id,
                    "document_id": document.id,
                    "title": document.title,
                    "authors": authors,
                    "keywords": self._loads_json_list(document.keywords_json),
                    "year": document.year,
                    "venue": document.venue,
                    "abstract": document.abstract,
                    "doi": document.doi,
                    "url": document.url,
                    "citation_text_default": document.citation_text_default,
                    "publisher": document.publisher,
                    "publisher_place": document.publisher_place,
                    "volume": document.volume,
                    "issue": document.issue,
                    "pages": document.pages,
                    "article_number": document.article_number,
                    "degree_institution": document.degree_institution,
                    "degree_location": document.degree_location,
                    "proceedings_title": document.proceedings_title,
                    "conference_name": document.conference_name,
                    "publication_date": document.publication_date,
                    "document_type": document.document_type,
                    "file_path": document.file_path,
                    "chunk_index": metadata.get("chunk_index"),
                    "section_type": metadata.get("section_type") or "",
                    "section_title": metadata.get("section_title") or "",
                    "section_chunk_index": metadata.get("section_chunk_index"),
                    "indexable": metadata.get("indexable", True),
                    "chunk_text": item.page_content,
                    "vector_rank": recall_rank,
                    "recall_rank": recall_rank,
                    "recall_source": "vector",
                }
            )
        return candidates

    def _merge_hybrid_candidates(
        self,
        *,
        vector_candidates: list[dict],
        keyword_candidates: list[dict],
        max_candidates: int,
        rrf_k: int,
    ) -> list[dict]:
        """用 RRF 融合向量召回和 BM25 召回，避免直接混合不同尺度分数。"""
        merged: dict[tuple[int, str], dict] = {}
        self._accumulate_rrf_candidates(
            merged,
            candidates=vector_candidates,
            rank_field="vector_rank",
            source_name="vector",
            rrf_k=rrf_k,
        )
        self._accumulate_rrf_candidates(
            merged,
            candidates=keyword_candidates,
            rank_field="keyword_rank",
            source_name="keyword",
            rrf_k=rrf_k,
        )

        fused_candidates = [payload["candidate"] for payload in merged.values()]
        fused_candidates.sort(
            key=lambda item: (
                float(item.get("hybrid_score") or 0.0),
                -int(item.get("best_recall_rank") or 0),
                -int(item.get("chunk_index") or 0),
            ),
            reverse=True,
        )
        for hybrid_rank, candidate in enumerate(fused_candidates):
            candidate["hybrid_rank"] = hybrid_rank
            candidate["recall_rank"] = hybrid_rank
        return fused_candidates[:max_candidates]

    def _accumulate_rrf_candidates(
        self,
        merged: dict[tuple[int, str], dict],
        *,
        candidates: list[dict],
        rank_field: str,
        source_name: str,
        rrf_k: int,
    ) -> None:
        """把一路召回候选累加到 RRF 融合容器中。"""
        for fallback_rank, candidate in enumerate(candidates):
            key = self._candidate_key(candidate)
            if key is None:
                continue
            rank = self._safe_rank(candidate.get(rank_field), fallback_rank)
            payload = merged.get(key)
            if payload is None:
                merged[key] = {
                    "candidate": dict(candidate),
                    "sources": {source_name},
                }
                payload = merged[key]

            fused_candidate = payload["candidate"]
            payload["sources"].add(source_name)
            fused_candidate[rank_field] = rank
            for diagnostic_field in ("keyword_score", "vector_rank", "keyword_rank"):
                if diagnostic_field in candidate and diagnostic_field not in fused_candidate:
                    fused_candidate[diagnostic_field] = candidate[diagnostic_field]
            fused_candidate["best_recall_rank"] = min(
                int(fused_candidate.get("best_recall_rank", rank)),
                rank,
            )
            fused_candidate["hybrid_score"] = float(fused_candidate.get("hybrid_score") or 0.0) + (
                1.0 / (rrf_k + rank + 1)
            )
            fused_candidate["recall_source"] = "+".join(sorted(payload["sources"]))

    def _candidate_key(self, candidate: dict) -> tuple[int, str] | None:
        """生成本地分块的去重键。"""
        try:
            document_id = int(candidate["document_id"])
        except (KeyError, TypeError, ValueError):
            return None
        try:
            chunk_index = int(candidate["chunk_index"])
            return document_id, str(chunk_index)
        except (KeyError, TypeError, ValueError):
            chunk_text = str(candidate.get("chunk_text") or "")
            return document_id, f"text:{hash(chunk_text)}"

    @staticmethod
    def _safe_rank(value: object, fallback_rank: int) -> int:
        """把召回排名规范为非负整数。"""
        try:
            rank = int(value)
        except (TypeError, ValueError):
            rank = fallback_rank
        return max(0, rank)

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        """计算阶段耗时毫秒。"""
        return int((time.perf_counter() - started_at) * 1000)

    def _build_rerank_trace_metadata(self, documents: list[dict]) -> dict[str, Any]:
        """从最终重排结果中提取工具链可展示的重排来源信息。"""
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

    def _loads_json_list(self, raw_value: str) -> list[str]:
        """Decode one JSON list column into a list of strings."""
        try:
            payload = json.loads(raw_value)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload if str(item).strip()]
