from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app_backend.db.connection import DatabaseManager
from app_backend.models import LibraryRecord


class LibraryRepository:
    """Repository for logical literature libraries."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the repository.

        Args:
            db_manager: Shared SQLite connection manager.
        """
        self.db_manager = db_manager

    def list_libraries(self) -> list[LibraryRecord]:
        """Return all libraries ordered by creation time."""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM libraries ORDER BY id ASC"
            ).fetchall()
            return [LibraryRecord(**dict(row)) for row in rows]

    def get_first_library(self) -> LibraryRecord | None:
        """Return the oldest existing library, or `None` when there is none."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM libraries ORDER BY id ASC LIMIT 1"
            ).fetchone()
            return LibraryRecord(**dict(row)) if row else None

    def get_by_id(self, library_id: int) -> LibraryRecord | None:
        """Fetch one library by primary key."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM libraries WHERE id = ?",
                (library_id,),
            ).fetchone()
            return LibraryRecord(**dict(row)) if row else None

    def create_library(
        self,
        *,
        name: str,
        description: str = "",
        folder_path: str = "",
        embedding_model: str | None = None,
        embedding_max_input_tokens: int | None = None,
        chunk_mode: str | None = None,
    ) -> LibraryRecord:
        """Create a new library and assign it a dedicated collection name."""
        now = datetime.now().isoformat(timespec="seconds")
        collection_name = f"library_{uuid4().hex[:12]}"
        resolved_embedding_model = self._require_non_empty_embedding_model(embedding_model)
        resolved_embedding_max_input_tokens = self._require_positive_embedding_limit(
            embedding_max_input_tokens
        )
        resolved_chunk_mode = (chunk_mode or "recursive").strip() or "recursive"
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO libraries(
                    name, description, folder_path, collection_name,
                    embedding_model, embedding_max_input_tokens, chunk_mode,
                    created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    folder_path,
                    collection_name,
                    resolved_embedding_model,
                    resolved_embedding_max_input_tokens,
                    resolved_chunk_mode,
                    now,
                    now,
                ),
            )
            library_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM libraries WHERE id = ?",
                (library_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to create library.")
            return LibraryRecord(**dict(row))

    def create_migration_library(
        self,
        *,
        name: str,
        description: str,
        folder_path: str,
        collection_name: str,
        embedding_model: str | None = None,
        embedding_max_input_tokens: int | None = None,
        chunk_mode: str | None = None,
    ) -> LibraryRecord:
        """Create a library with an explicit collection name for legacy migration."""
        now = datetime.now().isoformat(timespec="seconds")
        resolved_embedding_model = self._require_non_empty_embedding_model(embedding_model)
        resolved_embedding_max_input_tokens = self._require_positive_embedding_limit(
            embedding_max_input_tokens
        )
        resolved_chunk_mode = (chunk_mode or "recursive").strip() or "recursive"
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO libraries(
                    name, description, folder_path, collection_name,
                    embedding_model, embedding_max_input_tokens, chunk_mode,
                    created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    folder_path,
                    collection_name,
                    resolved_embedding_model,
                    resolved_embedding_max_input_tokens,
                    resolved_chunk_mode,
                    now,
                    now,
                ),
            )
            library_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM libraries WHERE id = ?",
                (library_id,),
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to create migration library.")
            return LibraryRecord(**dict(row))

    def update_library(
        self,
        library_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        folder_path: str | None = None,
        embedding_model: str | None = None,
        embedding_max_input_tokens: int | None = None,
        chunk_mode: str | None = None,
    ) -> bool:
        """Update mutable library fields."""
        updates: list[str] = []
        values: list[object] = []

        if name is not None:
            updates.append("name = ?")
            values.append(name)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if folder_path is not None:
            updates.append("folder_path = ?")
            values.append(folder_path)
        if embedding_model is not None:
            updates.append("embedding_model = ?")
            values.append(embedding_model)
        if embedding_max_input_tokens is not None:
            updates.append("embedding_max_input_tokens = ?")
            values.append(int(embedding_max_input_tokens))
        if chunk_mode is not None:
            updates.append("chunk_mode = ?")
            values.append(chunk_mode)

        if not updates:
            return False

        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat(timespec="seconds"))
        values.append(library_id)

        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                f"UPDATE libraries SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            return cursor.rowcount > 0

    def count_sessions_for_library(self, library_id: int) -> int:
        """Return how many chat sessions still reference one library."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(1) AS session_count FROM chat_sessions WHERE library_id = ?",
                (library_id,),
            ).fetchone()
            return int(row["session_count"]) if row else 0

    def delete_library(self, library_id: int) -> bool:
        """Delete one library and its owned documents, chunks, and sync history."""
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                DELETE FROM library_sync_items
                WHERE job_id IN (
                    SELECT id FROM library_sync_jobs WHERE library_id = ?
                )
                """,
                (library_id,),
            )
            connection.execute(
                "DELETE FROM library_sync_jobs WHERE library_id = ?",
                (library_id,),
            )
            try:
                connection.execute(
                    "DELETE FROM document_chunks_fts WHERE library_id = ?",
                    (library_id,),
                )
            except Exception:
                pass
            connection.execute(
                "DELETE FROM document_chunks WHERE library_id = ?",
                (library_id,),
            )
            connection.execute(
                "DELETE FROM documents WHERE library_id = ?",
                (library_id,),
            )
            cursor = connection.execute(
                "DELETE FROM libraries WHERE id = ?",
                (library_id,),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _require_non_empty_embedding_model(value: str | None) -> str:
        """校验文献库级向量模型，禁止仓储层静默写入默认模型。"""
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError("Embedding model cannot be empty.")
        return normalized

    @staticmethod
    def _require_positive_embedding_limit(value: int | None) -> int:
        """校验文献库级向量模型输入上限，禁止仓储层静默写入默认分块长度。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("embedding_max_input_tokens must be a positive integer.") from exc
        if parsed <= 0:
            raise ValueError("embedding_max_input_tokens must be a positive integer.")
        return parsed
