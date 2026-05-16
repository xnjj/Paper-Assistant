from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager
from app_backend.models import DocumentRecord


class DocumentRepository:
    """Repository for structured document and chunk persistence."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the document repository.

        Args:
            db_manager: Shared SQLite connection manager.
        """
        self.db_manager = db_manager

    def get_by_file_hash(self, library_id: int, file_hash: str) -> DocumentRecord | None:
        """Look up one document inside a specific library by file hash."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE library_id = ? AND file_hash = ?",
                (library_id, file_hash),
            ).fetchone()
            return DocumentRecord(**dict(row)) if row else None

    def get_by_id(self, document_id: int) -> DocumentRecord | None:
        """Fetch one document by primary key."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            return DocumentRecord(**dict(row)) if row else None

    def create_document(
        self,
        *,
        library_id: int,
        file_hash: str,
        file_path: str,
        file_name: str,
        title: str,
        abstract: str,
        authors: list[str],
        keywords: list[str],
        year: str,
        doi: str,
        url: str,
        venue: str,
        citation_text_default: str,
        source_type: str,
        source_uri: str,
        content_text: str,
        status: str,
    ) -> int:
        """Insert one document into a target library."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents(
                    library_id, file_hash, file_path, file_name, title, abstract,
                    authors_json, keywords_json, year, doi, url, venue,
                    citation_text_default, source_type, source_uri, content_text,
                    status, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    library_id,
                    file_hash,
                    file_path,
                    file_name,
                    title,
                    abstract,
                    json.dumps(authors, ensure_ascii=False),
                    json.dumps(keywords, ensure_ascii=False),
                    year,
                    doi,
                    url,
                    venue,
                    citation_text_default,
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
        library_id: int,
        document_id: int,
        chunk_index: int,
        chunk_text: str,
        token_count: int,
        vector_id: str,
        embedding_model: str,
    ) -> None:
        """Persist one chunk record for a document."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO document_chunks(
                    library_id, document_id, chunk_index, chunk_text, token_count,
                    vector_id, embedding_model, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    library_id,
                    document_id,
                    chunk_index,
                    chunk_text,
                    token_count,
                    vector_id,
                    embedding_model,
                    now,
                ),
            )

    def count_chunks(self, document_id: int) -> int:
        """Return the number of stored chunks for one document."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM document_chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            return int(row["count"]) if row else 0

    def delete_chunks(self, document_id: int) -> None:
        """Delete all structured chunk rows for one document."""
        with self.db_manager.get_connection() as connection:
            connection.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,),
            )

    def delete_document(self, document_id: int) -> bool:
        """Delete one document row by primary key."""
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (document_id,),
            )
            return cursor.rowcount > 0

    def update_document_index_state(
        self,
        document_id: int,
        *,
        status: str,
        content_text: str | None = None,
    ) -> None:
        """Update index-related fields for one document.

        Args:
            document_id: Target document primary key.
            status: New index lifecycle status such as `indexing`, `indexed`,
                or `index_failed`.
            content_text: Optional refreshed full text extracted from the PDF.
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            if content_text is None:
                connection.execute(
                    """
                    UPDATE documents
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, now, document_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE documents
                    SET content_text = ?, status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (content_text, status, now, document_id),
                )

    def list_documents(self, library_id: int | None = None) -> list[DocumentRecord]:
        """List all documents or only the documents for one library."""
        with self.db_manager.get_connection() as connection:
            if library_id is None:
                rows = connection.execute(
                    "SELECT * FROM documents ORDER BY id ASC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM documents WHERE library_id = ? ORDER BY id ASC",
                    (library_id,),
                ).fetchall()
            return [DocumentRecord(**dict(row)) for row in rows]

    def count_documents(self, library_id: int) -> int:
        """Return the number of documents currently stored in a library."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE library_id = ?",
                (library_id,),
            ).fetchone()
            return int(row["count"]) if row else 0

    def list_document_summaries(self, library_id: int) -> list[dict]:
        """Return lightweight document rows for one library ordered by update time."""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, file_path, updated_at
                FROM documents
                WHERE library_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (library_id,),
            ).fetchall()
            return [dict(row) for row in rows]
