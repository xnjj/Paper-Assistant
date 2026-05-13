from __future__ import annotations

from app_backend.models import MemoryRecord
from app_backend.repositories.memory_repository import MemoryRepository


class MemoryService:
    """记忆服务。

    当前版本提供：
    - 记忆保存
    - 作用域过滤查询
    - 基于简单关键词重叠的记忆召回
    """

    def __init__(self, memory_repository: MemoryRepository) -> None:
        """初始化记忆服务。

        Args:
            memory_repository: 记忆仓储实例。
        """
        self.memory_repository = memory_repository

    def save_memory(
        self,
        *,
        scope: str,
        memory_type: str,
        content: str,
        summary: str,
        session_id: int | None = None,
        importance: int = 1,
    ) -> int:
        """保存一条记忆。

        Args:
            scope: 记忆作用域，如 `global` 或 `session`。
            memory_type: 记忆类型。
            content: 原始记忆内容。
            summary: 简要摘要。
            session_id: 会话主键；全局记忆可为空。
            importance: 重要性分值。

        Returns:
            int: 新记忆主键。
        """
        return self.memory_repository.create_memory(
            scope=scope,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            summary=summary,
            importance=importance,
        )

    def list_memories(self, scope: str | None = None, session_id: int | None = None) -> list[MemoryRecord]:
        """读取记忆列表。

        Args:
            scope: 可选记忆作用域。
            session_id: 可选会话主键。

        Returns:
            list[MemoryRecord]: 按重要度排序的记忆记录。
        """
        return self.memory_repository.list_memories(scope, session_id=session_id)

    def recall_memories(self, query: str, session_id: int | None = None, limit: int = 5) -> list[MemoryRecord]:
        """根据当前用户输入召回最相关的记忆。

        这里先使用简单的关键词重叠评分，后续如果你需要更强的记忆检索，
        可以把这一层替换为独立向量库或更精细的排序器。

        Args:
            query: 用户当前输入。
            session_id: 当前会话主键，用于召回 session 级记忆。
            limit: 返回的最大条数。

        Returns:
            list[MemoryRecord]: 召回到的记忆列表。
        """
        candidates: list[MemoryRecord] = []
        candidates.extend(self.memory_repository.list_memories(scope="global"))
        if session_id is not None:
            candidates.extend(self.memory_repository.list_memories(scope="session", session_id=session_id))

        query_tokens = self._tokenize(query)
        scored: list[tuple[int, MemoryRecord]] = []
        for memory in candidates:
            haystack = f"{memory.summary} {memory.content}"
            memory_tokens = self._tokenize(haystack)
            overlap = len(query_tokens & memory_tokens)
            score = overlap * 10 + int(memory.importance)
            if score > 0:
                scored.append((score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [memory for _, memory in scored[:limit]]
        self.memory_repository.touch_memories([memory.id for memory in selected])
        return selected

    def _tokenize(self, text: str) -> set[str]:
        """把文本转为简单 token 集合。

        Args:
            text: 原始文本。

        Returns:
            set[str]: 小写、去重后的 token 集合。
        """
        tokens = [token.strip().lower() for token in text.replace("\n", " ").split(" ") if token.strip()]
        return set(tokens)
