from __future__ import annotations

import re
from collections import Counter
from typing import Any


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

    def rerank(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
        max_chunks_per_document: int = 2,
    ) -> list[dict[str, Any]]:
        """Rerank chunk candidates and return the final shortlist.

        Args:
            query: User retrieval query.
            candidates: Vector-recalled chunk candidates enriched with metadata.
            top_k: Final number of results to keep.
            max_chunks_per_document: Maximum number of chunks kept per document
                after reranking, to reduce one-document domination.
        """
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
            scored_candidates.append(enriched)

        scored_candidates.sort(
            key=lambda item: (
                item["rerank_score"],
                -int(item.get("recall_rank") or 0),
                -int(item.get("chunk_index") or 0),
            ),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []
        document_counts: Counter[int] = Counter()
        for candidate in scored_candidates:
            document_id = int(candidate["document_id"])
            if document_counts[document_id] >= max_chunks_per_document:
                continue
            selected.append(candidate)
            document_counts[document_id] += 1
            if len(selected) >= top_k:
                break
        return selected

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
