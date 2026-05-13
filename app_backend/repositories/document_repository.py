from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager
from app_backend.models import DocumentRecord


class DocumentRepository:
    """文献主表与切片表仓储。"""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初始化文献仓储。

        Args:
            db_manager: SQLite 连接管理器。
        """
        self.db_manager = db_manager

    def get_by_file_hash(self, file_hash: str) -> DocumentRecord | None:
        """根据文件哈希查重。

        Args:
            file_hash: 文件内容哈希值。

        Returns:
            DocumentRecord | None: 命中时返回文献记录，否则返回 `None`。
        """
        with self.db_manager.get_connection() as connection:
            row = connection.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,)).fetchone()
            return DocumentRecord(**dict(row)) if row else None

    def get_by_id(self, document_id: int) -> DocumentRecord | None:
        """根据主键读取单篇文献。

        Args:
            document_id: `documents` 表中的主键。

        Returns:
            DocumentRecord | None: 命中时返回文献记录，否则返回 `None`。
        """
        with self.db_manager.get_connection() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            return DocumentRecord(**dict(row)) if row else None

    def create_document(
        self,
        *,
        file_hash: str,
        file_path: str,
        file_name: str,
        title: str,
        abstract: str,
        authors: list[str],
        keywords: list[str],
        doi: str,
        source_type: str,
        source_uri: str,
        content_text: str,
        status: str,
    ) -> int:
        """插入一篇新文献并返回主键。

        Args:
            file_hash: 文件内容哈希。
            file_path: 本地文件路径。
            file_name: 文件名。
            title: 论文标题。
            abstract: 论文摘要。
            authors: 作者列表。
            keywords: 关键词列表。
            doi: DOI 标识符。
            source_type: 文献来源类型，如 `upload` 或 `local_folder`。
            source_uri: 来源地址或原始路径。
            content_text: 原文或清洗后的正文。
            status: 当前处理状态。

        Returns:
            int: 新插入文献的数据库主键。
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents(
                    file_hash, file_path, file_name, title, abstract,
                    authors_json, keywords_json, doi, source_type, source_uri,
                    content_text, status, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_hash,
                    file_path,
                    file_name,
                    title,
                    abstract,
                    json.dumps(authors, ensure_ascii=False),
                    json.dumps(keywords, ensure_ascii=False),
                    doi,
                    source_type,
                    source_uri,
                    content_text,
                    status,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def add_chunk(
        self,
        *,
        document_id: int,
        chunk_index: int,
        chunk_text: str,
        token_count: int,
        vector_id: str,
        embedding_model: str,
    ) -> None:
        """为文献写入一条切片记录。

        Args:
            document_id: 所属文献主键。
            chunk_index: 切片序号。
            chunk_text: 切片正文。
            token_count: 当前切片长度。
            vector_id: 向量库中的唯一 id。
            embedding_model: 当前使用的 embedding 模型名。
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO document_chunks(
                    document_id, chunk_index, chunk_text, token_count,
                    vector_id, embedding_model, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (document_id, chunk_index, chunk_text, token_count, vector_id, embedding_model, now),
            )

    def list_documents(self) -> list[DocumentRecord]:
        """返回所有已入库文献。"""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute("SELECT * FROM documents ORDER BY id ASC").fetchall()
            return [DocumentRecord(**dict(row)) for row in rows]
