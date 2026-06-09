from __future__ import annotations

import re
from collections import Counter
from typing import Any

import config_data as config
from app_backend.services.qwen_rerank_service import QwenRerankService


_QUERY_WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{1,}")
_CHINESE_BLOCK_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)


class RerankService:
    """Lightweight metadata-aware reranker for retrieved paper chunks.

    The current implementation is intentionally deterministic and dependency-light:
    it uses query/document token overlap, phrase bonuses, metadata matches, and
    the original vector recall order to reorder candidate chunks.
    """

    def __init__(self, qwen_rerank_service: QwenRerankService | None = None) -> None:
        """初始化重排服务；qwen_rerank_service 为空时只使用规则重排。"""
        self.qwen_rerank_service = qwen_rerank_service

    def rerank(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
        max_chunks_per_document: int | None = None,
    ) -> list[dict[str, Any]]:
        """Rerank chunk candidates and return the final shortlist.

        Args:
            query: User retrieval query.
            candidates: Vector-recalled chunk candidates enriched with metadata.
            top_k: Final number of results to keep.
            max_chunks_per_document: 每篇文献保留的最大分块数；为空时不限制。
        """
        if self._should_use_qwen_rerank():
            try:
                return self._rerank_with_qwen(
                    query=query,
                    candidates=candidates,
                    top_k=top_k,
                    max_chunks_per_document=max_chunks_per_document,
                )
            except Exception as exc:
                if not config.RERANK_FALLBACK_TO_RULE:
                    raise
                fallback_results = self._rerank_by_rule(
                    query=query,
                    candidates=candidates,
                    top_k=top_k,
                    max_chunks_per_document=max_chunks_per_document,
                )
                for item in fallback_results:
                    item["rerank_provider"] = "rule"
                    item["rerank_fallback_used"] = True
                    item["rerank_error"] = str(exc)
                return fallback_results

        return self._rerank_by_rule(
            query=query,
            candidates=candidates,
            top_k=top_k,
            max_chunks_per_document=max_chunks_per_document,
        )

    def _rerank_by_rule(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
        max_chunks_per_document: int | None,
    ) -> list[dict[str, Any]]:
        """使用本地规则重排候选分块。"""
        query_features = self._build_query_features(query)
        scored_candidates: list[dict[str, Any]] = []

        for recall_rank, candidate in enumerate(candidates):
            score = self._score_candidate(
                query_features=query_features,
                candidate=candidate,
                recall_rank=recall_rank,
            )
            enriched = dict(candidate)
            enriched["recall_rank"] = recall_rank
            enriched["rerank_score"] = round(score, 4)
            enriched["rerank_provider"] = "rule"
            enriched["rerank_fallback_used"] = False
            scored_candidates.append(enriched)

        scored_candidates.sort(
            key=lambda item: (
                item["rerank_score"],
                -int(item.get("recall_rank") or 0),
                -int(item.get("chunk_index") or 0),
            ),
            reverse=True,
        )

        return self._select_top_chunks(
            scored_candidates,
            top_k=top_k,
            max_chunks_per_document=max_chunks_per_document,
        )

    def _rerank_with_qwen(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
        max_chunks_per_document: int | None,
    ) -> list[dict[str, Any]]:
        """使用 qwen3-rerank 对本地候选分块做语义重排。"""
        if self.qwen_rerank_service is None:
            raise RuntimeError("qwen3-rerank 服务未初始化。")

        limited_candidates = candidates[: max(1, int(config.RERANK_MAX_DOCUMENTS))]
        documents = [self._build_rerank_document_text(candidate) for candidate in limited_candidates]
        rerank_results = self.qwen_rerank_service.rerank(
            query=query,
            documents=documents,
            top_n=len(documents),
        )
        if not rerank_results:
            raise RuntimeError("qwen3-rerank 未返回有效重排结果。")

        ranked_candidates: list[dict[str, Any]] = []
        for rerank_rank, result in enumerate(rerank_results):
            candidate = dict(limited_candidates[result.index])
            candidate["rerank_rank"] = rerank_rank
            candidate["rerank_score"] = round(result.relevance_score, 6)
            candidate["qwen_rerank_score"] = round(result.relevance_score, 6)
            candidate["rerank_provider"] = config.RERANK_MODEL_NAME
            candidate["rerank_fallback_used"] = False
            ranked_candidates.append(candidate)

        return self._select_top_chunks(
            ranked_candidates,
            top_k=top_k,
            max_chunks_per_document=max_chunks_per_document,
        )

    def _select_top_chunks(
        self,
        candidates: list[dict[str, Any]],
        *,
        top_k: int,
        max_chunks_per_document: int | None,
    ) -> list[dict[str, Any]]:
        """截取最终候选；未配置单篇上限时只按 top_k 保留。"""
        if max_chunks_per_document is None or max_chunks_per_document <= 0:
            return candidates[:top_k]

        selected: list[dict[str, Any]] = []
        document_counts: Counter[int] = Counter()
        for candidate in candidates:
            document_id = int(candidate["document_id"])
            if document_counts[document_id] >= max_chunks_per_document:
                continue
            selected.append(candidate)
            document_counts[document_id] += 1
            if len(selected) >= top_k:
                break
        return selected

    def _should_use_qwen_rerank(self) -> bool:
        """判断当前配置是否启用 qwen3-rerank。"""
        provider = str(getattr(config, "RERANK_PROVIDER", "rule") or "rule").strip().lower()
        return provider == "qwen" and self.qwen_rerank_service is not None

    def _build_rerank_document_text(self, candidate: dict[str, Any]) -> str:
        """把候选分块拼成更适合重排模型判断的文本。"""
        parts = [
            f"标题：{candidate.get('title') or ''}",
            f"摘要：{candidate.get('abstract') or ''}",
            f"章节类型：{candidate.get('section_type') or ''}",
            f"章节标题：{candidate.get('section_title') or ''}",
            f"正文片段：{candidate.get('chunk_text') or ''}",
        ]
        text = "\n".join(part.strip() for part in parts if part.strip())
        max_chars = max(1, int(getattr(config, "RERANK_MAX_DOC_CHARS", 3000)))
        return text[:max_chars].strip()

    def rerank_external_papers(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """对外部 paper 级候选做统一重排，避免直接混用不同数据源的相关性分数。"""
        if self._should_use_qwen_rerank():
            try:
                return self._rerank_external_with_qwen(
                    query=query,
                    candidates=candidates,
                    top_k=top_k,
                )
            except Exception as exc:
                if not config.RERANK_FALLBACK_TO_RULE:
                    raise
                fallback_results = self._rerank_external_by_rule(
                    query=query,
                    candidates=candidates,
                    top_k=top_k,
                )
                for item in fallback_results:
                    item["rerank_provider"] = "rule"
                    item["rerank_fallback_used"] = True
                    item["rerank_error"] = str(exc)
                return fallback_results

        return self._rerank_external_by_rule(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )

    def _rerank_external_by_rule(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """使用本地规则重排外部论文候选。"""
        query_features = self._build_query_features(query)
        scored_candidates: list[dict[str, Any]] = []

        for recall_rank, candidate in enumerate(candidates):
            prepared_candidate = dict(candidate)
            prepared_candidate["chunk_text"] = prepared_candidate.get("chunk_text") or prepared_candidate.get("abstract") or ""
            prepared_candidate["source_relevance_score"] = prepared_candidate.get("rerank_score")
            score = self._score_candidate(
                query_features=query_features,
                candidate=prepared_candidate,
                recall_rank=recall_rank,
            )
            prepared_candidate["recall_rank"] = recall_rank
            prepared_candidate["rerank_score"] = round(score, 4)
            prepared_candidate["rerank_provider"] = "rule"
            prepared_candidate["rerank_fallback_used"] = False
            scored_candidates.append(prepared_candidate)

        scored_candidates.sort(
            key=lambda item: (
                item["rerank_score"],
                -int(item.get("recall_rank") or 0),
            ),
            reverse=True,
        )
        return scored_candidates[:top_k]

    def _rerank_external_with_qwen(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """使用 qwen3-rerank 对外部 paper 级候选做语义重排。"""
        if self.qwen_rerank_service is None:
            raise RuntimeError("qwen3-rerank 服务未初始化。")

        limited_candidates = candidates[: max(1, int(config.RERANK_MAX_DOCUMENTS))]
        documents = [self._build_external_rerank_document_text(candidate) for candidate in limited_candidates]
        rerank_results = self.qwen_rerank_service.rerank(
            query=query,
            documents=documents,
            top_n=min(top_k, len(documents)),
        )
        if not rerank_results:
            raise RuntimeError("qwen3-rerank 未返回有效外部文献重排结果。")

        ranked_candidates: list[dict[str, Any]] = []
        for rerank_rank, result in enumerate(rerank_results):
            candidate = dict(limited_candidates[result.index])
            candidate["recall_rank"] = result.index
            candidate["rerank_rank"] = rerank_rank
            candidate["rerank_score"] = round(result.relevance_score, 6)
            candidate["qwen_rerank_score"] = round(result.relevance_score, 6)
            candidate["rerank_provider"] = config.RERANK_MODEL_NAME
            candidate["rerank_fallback_used"] = False
            ranked_candidates.append(candidate)
        return ranked_candidates[:top_k]

    def _build_external_rerank_document_text(self, candidate: dict[str, Any]) -> str:
        """把外部论文候选拼成适合重排模型判断的 paper 级文本。"""
        metadata_sources = candidate.get("metadata_sources")
        source_text = ", ".join(str(item) for item in metadata_sources) if isinstance(metadata_sources, list) else ""
        parts = [
            f"标题：{candidate.get('title') or ''}",
            f"摘要：{candidate.get('abstract') or candidate.get('chunk_text') or ''}",
            f"年份：{candidate.get('year') or ''}",
            f"来源：{source_text or candidate.get('source_type') or ''}",
            f"期刊/会议：{candidate.get('venue') or ''}",
            f"DOI：{candidate.get('doi') or ''}",
            f"URL：{candidate.get('url') or ''}",
        ]
        text = "\n".join(part.strip() for part in parts if part.strip())
        max_chars = max(1, int(getattr(config, "RERANK_MAX_DOC_CHARS", 3000)))
        return text[:max_chars].strip()

    def _score_candidate(
        self,
        *,
        query_features: dict[str, Any],
        candidate: dict[str, Any],
        recall_rank: int,
    ) -> float:
        """Score one candidate using metadata-aware lexical matching."""
        title = str(candidate.get("title") or "")
        abstract = str(candidate.get("abstract") or "")
        chunk_text = str(candidate.get("chunk_text") or "")
        venue = str(candidate.get("venue") or "")
        citation = str(candidate.get("citation_text_default") or "")
        authors = [str(author) for author in candidate.get("authors", [])]
        year = str(candidate.get("year") or "")
        doi = str(candidate.get("doi") or "")

        title_tokens = self._tokenize(title)
        abstract_tokens = self._tokenize(abstract)
        chunk_tokens = self._tokenize(chunk_text)
        venue_tokens = self._tokenize(venue)
        author_tokens = self._tokenize(" ".join(authors))
        citation_tokens = self._tokenize(citation)

        score = 0.0
        score += 8.0 * self._overlap_ratio(query_features["tokens"], title_tokens)
        score += 3.5 * self._overlap_ratio(query_features["tokens"], abstract_tokens)
        score += 6.0 * self._overlap_ratio(query_features["tokens"], chunk_tokens)
        score += 2.5 * self._overlap_ratio(query_features["tokens"], venue_tokens)
        score += 2.0 * self._overlap_ratio(query_features["tokens"], author_tokens)
        score += 2.0 * self._overlap_ratio(query_features["tokens"], citation_tokens)

        score += 5.0 * self._phrase_bonus(query_features["phrases"], title)
        score += 3.5 * self._phrase_bonus(query_features["phrases"], chunk_text)
        score += 2.0 * self._phrase_bonus(query_features["phrases"], abstract)

        if year and year in query_features["years"]:
            score += 5.0
        if doi and query_features["doi"] and query_features["doi"].lower() in doi.lower():
            score += 8.0

        query_text = query_features["raw"]
        lowered_query = query_text.lower()
        if venue and venue.lower() in lowered_query:
            score += 3.5
        if any(author.lower() in lowered_query for author in authors if len(author) >= 2):
            score += 4.0

        # Keep a light prior from the vector stage instead of discarding it entirely.
        score += 2.5 / (recall_rank + 1)

        chunk_index = candidate.get("chunk_index")
        if isinstance(chunk_index, int):
            score += 1.0 / (chunk_index + 2)

        return score

    def _build_query_features(self, query: str) -> dict[str, Any]:
        """Extract lexical and metadata-like features from a user query."""
        normalized = query.strip()
        return {
            "raw": normalized,
            "tokens": self._tokenize(normalized),
            "phrases": self._phrases(normalized),
            "years": set(_YEAR_PATTERN.findall(normalized)),
            "doi": self._extract_doi(normalized),
        }

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize mixed Chinese/English text for retrieval matching."""
        if not text:
            return set()

        tokens: set[str] = set()
        lowered = text.lower()

        for word in _QUERY_WORD_PATTERN.findall(lowered):
            tokens.add(word)

        for block in _CHINESE_BLOCK_PATTERN.findall(text):
            cleaned = block.strip()
            if len(cleaned) <= 8:
                tokens.add(cleaned)
            for n in (2, 3):
                if len(cleaned) < n:
                    continue
                for index in range(len(cleaned) - n + 1):
                    tokens.add(cleaned[index:index + n])
        return tokens

    def _phrases(self, text: str) -> list[str]:
        """Build a small list of important full-phrase matches."""
        phrases: list[str] = []
        for block in _CHINESE_BLOCK_PATTERN.findall(text):
            cleaned = block.strip()
            if len(cleaned) >= 4:
                phrases.append(cleaned)
        for word in _QUERY_WORD_PATTERN.findall(text.lower()):
            if len(word) >= 4:
                phrases.append(word)
        return phrases[:8]

    def _overlap_ratio(self, query_tokens: set[str], document_tokens: set[str]) -> float:
        """Return the fraction of query tokens found in one candidate field."""
        if not query_tokens or not document_tokens:
            return 0.0
        overlap = len(query_tokens & document_tokens)
        return overlap / max(1, len(query_tokens))

    def _phrase_bonus(self, phrases: list[str], text: str) -> float:
        """Return a small additive bonus for exact phrase presence."""
        if not phrases or not text:
            return 0.0
        lowered_text = text.lower()
        matched = 0
        for phrase in phrases:
            if phrase.lower() in lowered_text:
                matched += 1
        return min(1.0, matched / max(1, len(phrases)))

    def _extract_doi(self, text: str) -> str:
        """Extract one DOI fragment from the query when present."""
        match = _DOI_PATTERN.search(text)
        return match.group(0) if match else ""
