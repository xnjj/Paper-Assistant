from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager
from app_backend.models import MessageRecord, SessionRecord


class SessionRepository:
    """会话与消息仓储。"""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初始化会话仓储。

        Args:
            db_manager: SQLite 连接管理器。
        """
        self.db_manager = db_manager

    def create_session(self, title: str, user_goal: str) -> int:
        """创建一个新会话。

        Args:
            title: 会话标题。
            user_goal: 用户当前研究目标或任务描述。

        Returns:
            int: 新会话主键。
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO chat_sessions(title, user_goal, is_pinned, created_at, updated_at)
                VALUES(?, ?, 0, ?, ?)
                """,
                (title, user_goal, now, now),
            )
            return int(cursor.lastrowid)

    def get_session(self, session_id: int) -> SessionRecord | None:
        """读取单个会话。"""
        with self.db_manager.get_connection() as connection:
            row = connection.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
            return self._map_session(row) if row else None

    def list_sessions(self) -> list[SessionRecord]:
        """返回全部会话，置顶优先，其余按更新时间倒序。"""
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
        """更新会话标题。

        Args:
            session_id: 目标会话主键。
            title: 新标题。

        Returns:
            bool: 是否成功更新到记录。
        """
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
        """更新会话置顶状态。

        Args:
            session_id: 目标会话主键。
            is_pinned: 是否置顶。

        Returns:
            bool: 是否更新成功。
        """
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
        """删除会话及其关联消息和会话记忆。"""
        with self.db_manager.get_connection() as connection:
            connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
            cursor = connection.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def add_message(self, session_id: int, role: str, content: str, retrieval_context: dict | None = None) -> int:
        """向会话写入一条消息。"""
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
        """读取会话下的全部消息。"""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [MessageRecord(**dict(row)) for row in rows]

    @staticmethod
    def _map_session(row) -> SessionRecord:
        """把数据库行转换成会话记录对象。"""
        payload = dict(row)
        payload["is_pinned"] = bool(payload.get("is_pinned", 0))
        return SessionRecord(**payload)
