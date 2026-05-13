from __future__ import annotations

from datetime import datetime

from app_backend.db.connection import DatabaseManager
from app_backend.models import MemoryRecord


class MemoryRepository:
    """长期/短期记忆仓储。"""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """初始化记忆仓储。

        Args:
            db_manager: SQLite 连接管理器。
        """
        self.db_manager = db_manager

    def create_memory(
        self,
        *,
        scope: str,
        session_id: int | None,
        memory_type: str,
        content: str,
        summary: str,
        importance: int = 1,
    ) -> int:
        """创建一条记忆记录。

        Args:
            scope: 记忆作用域，如 `global` 或 `session`。
            session_id: 会话级记忆对应的会话主键，全局记忆时可为空。
            memory_type: 记忆类型，如 `preference`、`fact`、`research_topic`。
            content: 原始记忆内容。
            summary: 简短摘要，便于后续快速拼接上下文。
            importance: 重要性分值，数值越高优先级越高。

        Returns:
            int: 新记忆主键。
        """
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memories(scope, session_id, memory_type, content, summary, importance, last_used_at, created_at)
                VALUES(?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (scope, session_id, memory_type, content, summary, importance, now),
            )
            return int(cursor.lastrowid)

    def list_memories(self, scope: str | None = None, session_id: int | None = None) -> list[MemoryRecord]:
        """按作用域和会话过滤记忆。

        Args:
            scope: 可选记忆作用域。
            session_id: 可选会话主键。

        Returns:
            list[MemoryRecord]: 匹配到的记忆列表。
        """
        conditions: list[str] = []
        values: list[object] = []

        if scope is not None:
            conditions.append("scope = ?")
            values.append(scope)
        if session_id is not None:
            conditions.append("session_id = ?")
            values.append(session_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            "SELECT * FROM memories "
            f"{where_clause} "
            "ORDER BY importance DESC, created_at DESC"
        )

        with self.db_manager.get_connection() as connection:
            rows = connection.execute(sql, tuple(values)).fetchall()
            return [MemoryRecord(**dict(row)) for row in rows]

    def touch_memories(self, memory_ids: list[int]) -> None:
        """更新记忆的最近使用时间。

        Args:
            memory_ids: 本次被召回或使用的记忆主键列表。
        """
        if not memory_ids:
            return

        now = datetime.now().isoformat(timespec="seconds")
        placeholders = ", ".join("?" for _ in memory_ids)
        sql = f"UPDATE memories SET last_used_at = ? WHERE id IN ({placeholders})"

        with self.db_manager.get_connection() as connection:
            connection.execute(sql, (now, *memory_ids))
