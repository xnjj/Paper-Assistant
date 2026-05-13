from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_community.chat_models import ChatTongyi

from app_backend.models import MemoryRecord, MessageRecord, SessionRecord
from app_backend.repositories.session_repository import SessionRepository
from app_backend.services.memory_service import MemoryService
from app_backend.services.retriever_service import RetrieverService


class ChatService:
    """聊天编排服务。"""

    def __init__(
        self,
        session_repository: SessionRepository,
        memory_service: MemoryService,
        retriever_service: RetrieverService,
    ) -> None:
        self.session_repository = session_repository
        self.memory_service = memory_service
        self.retriever_service = retriever_service
        self.model = ChatTongyi(model="qwen3-max", streaming=True)

    def create_session(self, title: str, user_goal: str) -> SessionRecord:
        """创建新会话。"""
        session_id = self.session_repository.create_session(title=title, user_goal=user_goal)
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise RuntimeError("会话创建后读取失败。")
        return session

    def list_sessions(self) -> list[SessionRecord]:
        """列出全部会话。"""
        return self.session_repository.list_sessions()

    def list_messages(self, session_id: int) -> list[MessageRecord]:
        """列出指定会话的消息记录。"""
        return self.session_repository.list_messages(session_id)

    def rename_session(self, session_id: int, title: str) -> SessionRecord:
        """更新会话标题。"""
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("会话标题不能为空。")
        updated = self.session_repository.update_session_title(session_id, normalized_title)
        if not updated:
            raise ValueError(f"会话不存在: {session_id}")
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"会话不存在: {session_id}")
        return session

    def set_session_pinned(self, session_id: int, is_pinned: bool) -> SessionRecord:
        """更新会话置顶状态。"""
        updated = self.session_repository.update_session_pin_status(session_id, is_pinned)
        if not updated:
            raise ValueError(f"浼氳瘽涓嶅瓨鍦? {session_id}")
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"浼氳瘽涓嶅瓨鍦? {session_id}")
        return session

    def delete_session(self, session_id: int) -> None:
        """删除会话及其关联消息。"""
        deleted = self.session_repository.delete_session(session_id)
        if not deleted:
            raise ValueError(f"会话不存在: {session_id}")

    def chat(self, session_id: int, user_message: str, top_k: int = 5) -> dict[str, Any]:
        """执行一次普通聊天请求。"""
        context = self._prepare_chat_context(session_id=session_id, user_message=user_message, top_k=top_k)
        answer = self._invoke_model(context["prompt"])
        self._persist_chat_result(
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
        )
        return self._build_chat_response(
            session_id=session_id,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
        )

    def stream_chat(self, session_id: int, user_message: str, top_k: int = 5) -> Iterator[dict[str, Any]]:
        """执行一次流式聊天请求。"""
        context = self._prepare_chat_context(session_id=session_id, user_message=user_message, top_k=top_k)
        yield {
            "type": "meta",
            "session_id": session_id,
            "retrieved_memories": [self._memory_to_dict(memory) for memory in context["memories"]],
            "retrieved_documents": context["retrieved_docs"],
        }

        chunks: list[str] = []
        emitted_delta = False

        try:
            for chunk in self.model.stream(context["prompt"]):
                text = self._extract_stream_text(chunk)
                if not text:
                    continue
                for display_chunk in self._split_stream_text(text):
                    emitted_delta = True
                    chunks.append(display_chunk)
                    yield {"type": "delta", "content": display_chunk}
        except Exception as exc:
            print(f"stream chat failed, fallback to invoke: {exc}")

        if emitted_delta:
            answer = "".join(chunks)
        else:
            answer = self._invoke_model(context["prompt"])
            if answer:
                for display_chunk in self._split_stream_text(answer):
                    yield {"type": "delta", "content": display_chunk}

        self._persist_chat_result(
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
        )
        yield {"type": "done", "answer": answer}

    def _prepare_chat_context(self, session_id: int, user_message: str, top_k: int) -> dict[str, Any]:
        """准备本次对话的上下文。"""
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"会话不存在: {session_id}")

        memories = self.memory_service.recall_memories(user_message, session_id=session_id, limit=5)
        retrieved_docs = self.retriever_service.search(user_message, top_k=top_k)
        memory_context = self._format_memories(memories)
        document_context = self._format_documents(retrieved_docs)
        history_context = self._format_recent_messages(self.session_repository.list_messages(session_id))

        prompt = f"""
你是一个论文助手 agent，请结合会话历史、用户记忆和本地文献检索结果来回答问题。

当前会话目标：
{session.user_goal}

相关记忆：
{memory_context}

相关文献片段：
{document_context}

最近会话历史：
{history_context}

用户问题：
{user_message}

要求：
- 优先基于提供的文献片段回答。
- 如果依据不足，请明确说明。
- 回答使用中文。
- 如果引用了文献，请在正文中使用类似 [1] [2] [3] 的引用编号，并在最后写出“参考文献：”。
"""
        return {
            "session": session,
            "memories": memories,
            "retrieved_docs": retrieved_docs,
            "prompt": prompt,
        }

    def _persist_chat_result(
        self,
        *,
        session_id: int,
        user_message: str,
        answer: str,
        memories: list[MemoryRecord],
        retrieved_docs: list[dict[str, Any]],
    ) -> None:
        """持久化一次用户消息和对应助手回答。"""
        retrieval_context = {
            "memories": [self._memory_to_dict(memory) for memory in memories],
            "documents": retrieved_docs,
        }
        self.session_repository.add_message(session_id, "user", user_message)
        self.session_repository.add_message(session_id, "assistant", answer, retrieval_context=retrieval_context)

    def _build_chat_response(
        self,
        *,
        session_id: int,
        answer: str,
        memories: list[MemoryRecord],
        retrieved_docs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """构造普通聊天接口的标准返回结构。"""
        return {
            "session_id": session_id,
            "answer": answer,
            "retrieved_memories": [self._memory_to_dict(memory) for memory in memories],
            "retrieved_documents": retrieved_docs,
        }

    def _invoke_model(self, prompt: str) -> str:
        """执行一次非流式模型调用。"""
        response = self.model.invoke(prompt)
        return getattr(response, "content", str(response))

    def _extract_stream_text(self, chunk: Any) -> str:
        """从流式 chunk 中提取文本内容。"""
        content = getattr(chunk, "content", chunk)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "".join(parts)
        return str(content) if content else ""

    def _split_stream_text(self, text: str, max_chars: int = 24) -> list[str]:
        """把较大的流式片段再切小，提升前端渐进渲染效果。"""
        normalized_text = text.replace("\r\n", "\n")
        parts: list[str] = []
        current = ""

        for char in normalized_text:
            current += char
            if char in {"\n", "。", "！", "？", "；", "，", ",", ".", "!", "?", ";", ":"} or len(current) >= max_chars:
                parts.append(current)
                current = ""

        if current:
            parts.append(current)
        return parts

    def _format_memories(self, memories: list[MemoryRecord]) -> str:
        """将记忆列表格式化为提示词片段。"""
        if not memories:
            return "无"
        return "\n".join(f"- [{memory.memory_type}] {memory.summary}: {memory.content}" for memory in memories)

    def _format_documents(self, documents: list[dict[str, Any]]) -> str:
        """将检索到的文献片段格式化为提示词片段。"""
        if not documents:
            return "无"
        lines: list[str] = []
        for item in documents:
            lines.append(
                f"- 标题: {item['title']}\n"
                f"  摘要: {item['abstract']}\n"
                f"  片段: {item['chunk_text']}"
            )
        return "\n".join(lines)

    def _format_recent_messages(self, messages: list[MessageRecord], limit: int = 6) -> str:
        """提取最近若干条消息作为短期上下文。"""
        recent = messages[-limit:]
        if not recent:
            return "无"
        return "\n".join(f"{message.role}: {message.content}" for message in recent)

    def _memory_to_dict(self, memory: MemoryRecord) -> dict[str, Any]:
        """把记忆对象转换为可 JSON 返回的结构。"""
        return {
            "id": memory.id,
            "scope": memory.scope,
            "session_id": memory.session_id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "summary": memory.summary,
            "importance": memory.importance,
            "last_used_at": memory.last_used_at,
            "created_at": memory.created_at,
        }
