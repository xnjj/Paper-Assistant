from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from langchain_community.chat_models import ChatTongyi

import config_data as config
from app_backend.models import MemoryRecord, MessageRecord, SessionRecord
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.services.config_service import ConfigService
from app_backend.services.memory_service import MemoryService
from app_backend.services.retriever_service import RetrieverService

_SOURCE_TAG_PATTERN = re.compile(r"\[(?:@)?(doc_\d+)\]")
_REFERENCE_HEADING_PATTERN = re.compile(r"^\s*(?:参考文献|references)\s*[:：]?\s*$", re.IGNORECASE)


class ChatService:
    """Chat orchestration service."""

    def __init__(
        self,
        session_repository: SessionRepository,
        library_repository: LibraryRepository,
        memory_service: MemoryService,
        retriever_service: RetrieverService,
        config_service: ConfigService | None = None,
    ) -> None:
        self.session_repository = session_repository
        self.library_repository = library_repository
        self.memory_service = memory_service
        self.retriever_service = retriever_service
        self.config_service = config_service

    def create_session(self, title: str, user_goal: str, library_id: int | None = None) -> SessionRecord:
        """Create a new session bound to one library."""
        if library_id is None:
            raise ValueError("Please choose a library before creating a session.")

        target_library = self.library_repository.get_by_id(library_id)
        if target_library is None:
            raise ValueError(f"Library not found: {library_id}")

        session_id = self.session_repository.create_session(
            title=title,
            user_goal=user_goal,
            library_id=target_library.id,
        )
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise RuntimeError("Failed to reload the session after creation.")
        return session

    def list_sessions(self) -> list[SessionRecord]:
        """Return all chat sessions."""
        return self.session_repository.list_sessions()

    def list_messages(self, session_id: int) -> list[MessageRecord]:
        """Return the ordered message history for one session."""
        return self.session_repository.list_messages(session_id)

    def rename_session(self, session_id: int, title: str) -> SessionRecord:
        """Update the title of an existing session."""
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Session title cannot be empty.")
        updated = self.session_repository.update_session_title(session_id, normalized_title)
        if not updated:
            raise ValueError(f"Session not found: {session_id}")
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return session

    def set_session_pinned(self, session_id: int, is_pinned: bool) -> SessionRecord:
        """Update the pinned state of a session."""
        updated = self.session_repository.update_session_pin_status(session_id, is_pinned)
        if not updated:
            raise ValueError(f"Session not found: {session_id}")
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return session

    def delete_session(self, session_id: int) -> None:
        """Delete a session and its dependent message/memory records."""
        deleted = self.session_repository.delete_session(session_id)
        if not deleted:
            raise ValueError(f"Session not found: {session_id}")

    def chat(self, session_id: int, user_message: str, top_k: int = 5) -> dict[str, Any]:
        """Handle a non-streaming chat request."""
        context = self._prepare_chat_context(session_id=session_id, user_message=user_message, top_k=top_k)
        raw_answer = self._invoke_model(context["prompt"])
        answer, citations = self._finalize_answer(raw_answer, context["retrieved_docs"])
        self._persist_chat_result(
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
            citations=citations,
        )
        return self._build_chat_response(
            session_id=session_id,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
            citations=citations,
        )

    def stream_chat(self, session_id: int, user_message: str, top_k: int = 5) -> Iterator[dict[str, Any]]:
        """Handle a streaming chat request."""
        context = self._prepare_chat_context(session_id=session_id, user_message=user_message, top_k=top_k)
        yield {
            "type": "meta",
            "session_id": session_id,
            "library_id": context["session"].library_id,
            "retrieved_memories": [self._memory_to_dict(memory) for memory in context["memories"]],
            "retrieved_documents": context["retrieved_docs"],
        }

        chunks: list[str] = []
        emitted_delta = False

        try:
            for chunk in self._build_model(streaming=True).stream(context["prompt"]):
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
            raw_answer = "".join(chunks)
        else:
            raw_answer = self._invoke_model(context["prompt"])
            if raw_answer:
                for display_chunk in self._split_stream_text(raw_answer):
                    yield {"type": "delta", "content": display_chunk}

        answer, citations = self._finalize_answer(raw_answer, context["retrieved_docs"])
        self._persist_chat_result(
            session_id=session_id,
            user_message=user_message,
            answer=answer,
            memories=context["memories"],
            retrieved_docs=context["retrieved_docs"],
            citations=citations,
        )
        yield {"type": "done", "answer": answer, "citations": citations}

    def _prepare_chat_context(self, session_id: int, user_message: str, top_k: int) -> dict[str, Any]:
        """Build the prompt context for one chat turn."""
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        library = self.library_repository.get_by_id(session.library_id)
        if library is None:
            raise ValueError(f"Library not found: {session.library_id}")

        memories = self.memory_service.recall_memories(user_message, session_id=session_id, limit=5)
        effective_top_k = top_k if top_k > 0 else self._get_rerank_chunks()
        recall_k = self._get_recall_chunks()
        retrieved_docs = self.retriever_service.search(
            user_message,
            library_id=library.id,
            top_k=effective_top_k,
            recall_k=recall_k,
        )
        retrieved_docs = [self._attach_source_id(document) for document in retrieved_docs]

        memory_context = self._format_memories(memories)
        document_context = self._format_documents(retrieved_docs)
        history_context = self._format_recent_messages(self.session_repository.list_messages(session_id))

        prompt = f"""
你是论文助手 agent。请基于会话目标、历史消息、记忆和当前文献库检索结果，用中文严谨回答用户问题。

当前会话目标：
{session.user_goal}

当前文献库：
{library.name}

相关记忆：
{memory_context}

候选文献证据：
{document_context}

最近会话历史：
{history_context}

用户问题：
{user_message}

请严格遵守以下要求：
1. 优先依据已提供的文献证据作答，不要脱离证据自由发挥。
2. 如果现有证据不足，请明确说明“现有文献证据不足以支持该结论”，不要编造出处。
3. 回答正文使用中文，表达准确、克制、学术化。
4. 如果需要引用文献，只能使用候选文献中给出的 source_id，并在正文中写成 [@doc_x] 的形式，例如 [@doc_18]。
5. 不要自行生成 [1]、[2] 这类编号；编号和参考文献表将由系统统一生成。
6. 同一篇文献多次引用时，必须复用同一个 source_id。
7. 不要输出“参考文献”标题，也不要自行在文末手写参考文献列表；系统会根据你在正文中使用的 source_id 自动生成。
8. 不要引用未在候选文献证据中出现的 source_id。
9. 如果没有足够证据支持某个判断，请直接说明证据不足。
10. 不要输出“参考文献待补充”“cited in fragment”这类非正式占位文本。

请直接输出最终答案正文。
"""
        return {
            "session": session,
            "library": library,
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
        citations: list[dict[str, Any]],
    ) -> None:
        """Persist one user message and the paired assistant reply."""
        retrieval_context = {
            "memories": [self._memory_to_dict(memory) for memory in memories],
            "documents": retrieved_docs,
            "citations": citations,
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
        citations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the standard response payload for non-streaming chat."""
        session = self.session_repository.get_session(session_id)
        return {
            "session_id": session_id,
            "library_id": session.library_id if session else None,
            "answer": answer,
            "retrieved_memories": [self._memory_to_dict(memory) for memory in memories],
            "retrieved_documents": retrieved_docs,
            "citations": citations,
        }

    def _attach_source_id(self, document: dict[str, Any]) -> dict[str, Any]:
        """Attach one stable source identifier to a retrieved document."""
        payload = dict(document)
        payload["source_id"] = self._build_source_id(int(document["document_id"]))
        return payload

    def _build_source_id(self, document_id: int) -> str:
        """Build one source identifier consumed by the model."""
        return f"doc_{document_id}"

    def _finalize_answer(self, raw_answer: str, retrieved_docs: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """Normalize source tags into numbered citations and build the reference list."""
        body = self._strip_reference_section(raw_answer)
        ordered_bindings: list[dict[str, Any]] = []
        source_to_binding: dict[str, dict[str, Any]] = {}
        source_to_document = {
            str(document.get("source_id", "")): document
            for document in retrieved_docs
            if document.get("source_id")
        }

        def replace_tag(match: re.Match[str]) -> str:
            source_id = match.group(1)
            document = source_to_document.get(source_id)
            if document is None:
                return ""

            binding = source_to_binding.get(source_id)
            if binding is None:
                binding = self._build_citation_binding(
                    number=len(ordered_bindings) + 1,
                    source_id=source_id,
                    document=document,
                )
                source_to_binding[source_id] = binding
                ordered_bindings.append(binding)
            return f"[{binding['number']}]"

        normalized_body = _SOURCE_TAG_PATTERN.sub(replace_tag, body).strip()
        normalized_body = re.sub(r"[ \t]+\n", "\n", normalized_body)
        normalized_body = re.sub(r"\n{3,}", "\n\n", normalized_body)

        if not ordered_bindings:
            return normalized_body, []

        reference_section = self._build_reference_section(ordered_bindings)
        final_answer = f"{normalized_body}\n\n参考文献\n{reference_section}".strip()
        return final_answer, ordered_bindings

    def _build_citation_binding(
        self,
        *,
        number: int,
        source_id: str,
        document: dict[str, Any],
    ) -> dict[str, Any]:
        """Build one explicit citation binding record for the frontend."""
        return {
            "number": number,
            "source_id": source_id,
            "document_id": document.get("document_id"),
            "text": document.get("citation_text_default") or document.get("title") or "",
            "title": document.get("title") or "",
            "abstract": document.get("abstract") or "",
            "file_path": document.get("file_path") or "",
            "authors": document.get("authors") or [],
            "year": document.get("year") or "",
            "venue": document.get("venue") or "",
            "doi": document.get("doi") or "",
            "url": document.get("url") or "",
            "citation_text_default": document.get("citation_text_default") or "",
            "chunk_index": document.get("chunk_index"),
            "chunk_text": document.get("chunk_text") or "",
        }

    def _build_reference_section(self, citations: list[dict[str, Any]]) -> str:
        """Render the final numbered reference section."""
        return "\n".join(f"[{citation['number']}] {citation['text']}" for citation in citations)

    def _strip_reference_section(self, answer: str) -> str:
        """Remove any model-generated reference section before rebuilding it."""
        lines = (answer or "").splitlines()
        heading_index = next(
            (index for index, line in enumerate(lines) if _REFERENCE_HEADING_PATTERN.match(line.strip())),
            -1,
        )
        if heading_index >= 0:
            return "\n".join(lines[:heading_index]).strip()
        return answer.strip()

    def _invoke_model(self, prompt: str) -> str:
        """Execute one non-streaming model invocation."""
        response = self._build_model(streaming=False).invoke(prompt)
        return getattr(response, "content", str(response))

    def _build_model(self, *, streaming: bool) -> ChatTongyi:
        """Build one chat model instance from the active runtime config."""
        model_name = config.LLM_MODEL_NAME
        api_key = config.OPENAI_API_KEY
        if self.config_service is not None:
            model_name = self.config_service.get_llm_model_name()
            api_key = self.config_service.get_api_key()

        return ChatTongyi(
            model=model_name,
            api_key=api_key or None,
            streaming=streaming,
        )

    def _get_recall_chunks(self) -> int:
        """Return the configured recall candidate count."""
        if self.config_service is None:
            return 20
        return self.config_service.get_recall_chunks()

    def _get_rerank_chunks(self) -> int:
        """Return the configured final rerank result count."""
        if self.config_service is None:
            return 5
        return self.config_service.get_rerank_chunks()

    def _extract_stream_text(self, chunk: Any) -> str:
        """Extract displayable text from a streaming model chunk."""
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
        """Sub-split larger stream deltas for smoother UI rendering."""
        normalized_text = text.replace("\r\n", "\n")
        parts: list[str] = []
        current = ""

        for char in normalized_text:
            current += char
            if char in {"\n", "。", "！", "？", "，", ",", ".", "!", "?", ";", ":", "；", "："} or len(current) >= max_chars:
                parts.append(current)
                current = ""

        if current:
            parts.append(current)
        return parts

    def _format_memories(self, memories: list[MemoryRecord]) -> str:
        """Format memories into a prompt-friendly text block."""
        if not memories:
            return "无"
        return "\n".join(f"- [{memory.memory_type}] {memory.summary}: {memory.content}" for memory in memories)

    def _format_documents(self, documents: list[dict[str, Any]]) -> str:
        """Format retrieved chunks into a prompt-friendly text block."""
        if not documents:
            return "无"

        lines: list[str] = []
        for item in documents:
            authors = ", ".join(item.get("authors", [])) or "无"
            year = item.get("year") or "无"
            venue = item.get("venue") or "无"
            doi = item.get("doi") or "无"
            url = item.get("url") or "无"
            citation = item.get("citation_text_default") or "无"
            source_id = item.get("source_id") or self._build_source_id(int(item["document_id"]))
            lines.append(
                f"- 候选文献 source_id={source_id}\n"
                f"  标题: {item['title']}\n"
                f"  作者: {authors}\n"
                f"  年份: {year}\n"
                f"  来源: {venue}\n"
                f"  DOI: {doi}\n"
                f"  URL: {url}\n"
                f"  默认引用文本: {citation}\n"
                f"  若在正文中引用该文献，请写成 [@{source_id}]\n"
                f"  摘要: {item['abstract']}\n"
                f"  证据片段: {item['chunk_text']}"
            )
        return "\n".join(lines)

    def _format_recent_messages(self, messages: list[MessageRecord], limit: int = 6) -> str:
        """Use only the recent window of messages as short-term context."""
        recent = messages[-limit:]
        if not recent:
            return "无"
        return "\n".join(f"{message.role}: {message.content}" for message in recent)

    def _memory_to_dict(self, memory: MemoryRecord) -> dict[str, Any]:
        """Convert one memory record into a JSON-serializable dictionary."""
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
