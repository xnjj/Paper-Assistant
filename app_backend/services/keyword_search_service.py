from __future__ import annotations

import json
import sqlite3
from typing import Any

from app_backend.db.connection import DatabaseManager
from app_backend.utils.keyword_text import build_fts_match_expression, quote_fts_term


class KeywordSearchService:
    """基于 SQLite FTS5/BM25 的本地关键词召回服务。"""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初始化关键词召回服务。"""
        self.db_manager = db_manager

    def search(self, *, query: str, library_id: int, top_k: int) -> list[dict[str, Any]]:
        """按 library_id 和用户问题从 document_chunks_fts 召回候选分块。"""
        if not query.strip() or top_k <= 0:
            return []

        match_expression = build_fts_match_expression(query)
        if not match_expression:
            return []

        with self.db_manager.get_connection() as connection:
            try:
                rows = self._run_search_query(
                    connection,
                    library_id=library_id,
                    match_expression=match_expression,
                    top_k=top_k,
                )
            except sqlite3.OperationalError:
                fallback_expression = quote_fts_term(query.strip())
                try:
                    rows = self._run_search_query(
                        connection,
                        library_id=library_id,
                        match_expression=fallback_expression,
                        top_k=top_k,
                    )
                except sqlite3.OperationalError:
                    return []

        candidates: list[dict[str, Any]] = []
        for keyword_rank, row in enumerate(rows):
            candidates.append(self._row_to_candidate(row, library_id=library_id, keyword_rank=keyword_rank))
        return candidates

    def _run_search_query(
        self,
        connection,
        *,
        library_id: int,
        match_expression: str,
        top_k: int,
    ) -> list[sqlite3.Row]:
        """执行 FTS5 MATCH 查询；BM25 分数越小代表越相关。"""
        return connection.execute(
            """
            SELECT
                c.id AS chunk_row_id,
                c.library_id,
                c.document_id,
                c.chunk_index,
                c.section_type,
                c.section_title,
                c.section_chunk_index,
                c.indexable,
                c.chunk_text,
                d.title,
                d.abstract,
                d.authors_json,
                d.keywords_json,
                d.year,
                d.venue,
                d.doi,
                d.url,
                d.citation_text_default,
                d.publisher,
                d.publisher_place,
                d.volume,
                d.issue,
                d.pages,
                d.article_number,
                d.degree_institution,
                d.degree_location,
                d.proceedings_title,
                d.conference_name,
                d.publication_date,
                d.document_type,
                d.file_path,
                bm25(
                    document_chunks_fts,
                    0.0, 0.0, 0.0, 0.0,
                    8.0, 3.0, 6.0, 4.0, 1.0, 0.6
                ) AS bm25_score
            FROM document_chunks_fts
            JOIN document_chunks AS c ON c.id = document_chunks_fts.chunk_id
            JOIN documents AS d ON d.id = c.document_id
            WHERE document_chunks_fts MATCH ?
              AND document_chunks_fts.library_id = ?
              AND c.indexable = 1
            ORDER BY bm25_score ASC
            LIMIT ?
            """,
            (match_expression, library_id, top_k),
        ).fetchall()

    def _row_to_candidate(self, row: sqlite3.Row, *, library_id: int, keyword_rank: int) -> dict[str, Any]:
        """把数据库行转换为与向量召回一致的候选结构。"""
        return {
            "library_id": library_id,
            "document_id": int(row["document_id"]),
            "title": row["title"] or "",
            "authors": self._loads_json_list(row["authors_json"] or ""),
            "keywords": self._loads_json_list(row["keywords_json"] or ""),
            "year": row["year"] or "",
            "venue": row["venue"] or "",
            "abstract": row["abstract"] or "",
            "doi": row["doi"] or "",
            "url": row["url"] or "",
            "citation_text_default": row["citation_text_default"] or "",
            "publisher": row["publisher"] or "",
            "publisher_place": row["publisher_place"] or "",
            "volume": row["volume"] or "",
            "issue": row["issue"] or "",
            "pages": row["pages"] or "",
            "article_number": row["article_number"] or "",
            "degree_institution": row["degree_institution"] or "",
            "degree_location": row["degree_location"] or "",
            "proceedings_title": row["proceedings_title"] or "",
            "conference_name": row["conference_name"] or "",
            "publication_date": row["publication_date"] or "",
            "document_type": row["document_type"] or "",
            "file_path": row["file_path"] or "",
            "chunk_index": int(row["chunk_index"]),
            "section_type": row["section_type"] or "",
            "section_title": row["section_title"] or "",
            "section_chunk_index": int(row["section_chunk_index"] or 0),
            "indexable": bool(row["indexable"]),
            "chunk_text": row["chunk_text"] or "",
            "keyword_rank": keyword_rank,
            "keyword_score": float(row["bm25_score"] or 0.0),
            "recall_source": "keyword",
        }

    def _loads_json_list(self, raw_value: str) -> list[str]:
        """解析数据库中的 JSON 列表字段。"""
        try:
            payload = json.loads(raw_value)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload if str(item).strip()]
