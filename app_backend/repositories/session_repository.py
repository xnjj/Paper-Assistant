from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager
from app_backend.models import MessageRecord, SessionRecord


class SessionRepository:
    """Repository for chat sessions and messages."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the session repository.

        Args:
            db_manager: Shared SQLite connection manager.
        """
        self.db_manager = db_manager

    def create_session(self, title: str, user_goal: str, library_id: int) -> int:
        """Create a new chat session bound to one library."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_sessions(
                    library_id, title, user_goal, is_pinned, created_at, updated_at
                )
                VALUES(?, ?, ?, 0, ?, ?)
                """,
                (library_id, title, user_goal, now, now),
            )
            return int(cursor.lastrowid)

    def get_session(self, session_id: int) -> SessionRecord | None:
        """Fetch one session."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM chat_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            return self._map_session(row) if row else None

    def list_sessions(self) -> list[SessionRecord]:
        """Return all sessions, pinned first and then by recent activity."""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM chat_sessions
                ORDER BY is_pinned DESC, updated_at DESC, id DESC
                """
            ).fetchall()
            return [self._map_session(row) for row in rows]

    def update_session_title(self, session_id: int, title: str) -> bool:
        """Update the visible title of one session."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, now, session_id),
            )
            return cursor.rowcount > 0

    def update_session_pin_status(self, session_id: int, is_pinned: bool) -> bool:
        """Toggle the pinned state of a session."""
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE chat_sessions
                SET is_pinned = ?
                WHERE id = ?
                """,
                (1 if is_pinned else 0, session_id),
            )
            return cursor.rowcount > 0

    def delete_session(self, session_id: int) -> bool:
        """Delete a session together with its messages and session memories."""
        with self.db_manager.get_connection() as connection:
            connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
            cursor = connection.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def count_sessions_for_library(self, library_id: int) -> int:
        """Return how many sessions currently depend on a library."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM chat_sessions WHERE library_id = ?",
                (library_id,),
            ).fetchone()
            return int(row["count"]) if row else 0

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        retrieval_context: dict | None = None,
    ) -> int:
        """Append one chat message to a session."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_messages(session_id, role, content, retrieval_context_json, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (session_id, role, content, json.dumps(retrieval_context or {}, ensure_ascii=False), now),
            )
            connection.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            return int(cursor.lastrowid)

    def list_messages(self, session_id: int) -> list[MessageRecord]:
        """Return the full ordered message history for one session."""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [MessageRecord(**dict(row)) for row in rows]

    @staticmethod
    def _map_session(row) -> SessionRecord:
        """Convert one SQLite row into a session dataclass."""
        payload = dict(row)
        payload["is_pinned"] = bool(payload.get("is_pinned", 0))
        return SessionRecord(**payload)
