from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import asdict, is_dataclass
from typing import Any

from langchain_community.chat_models import ChatTongyi

import config_data as config
from app_backend.models import MemoryRecord, MessageRecord, SessionRecord
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.services.agent_orchestrator_service import AgentOrchestratorService
from app_backend.services.citation_formatter import format_gbt7714_citation
from app_backend.services.config_service import ConfigService
from app_backend.services.memory_service import MemoryService
from app_backend.services.retriever_service import RetrieverService

_SOURCE_TAG_PATTERN = re.compile(
    r"\[\s*((?:@?(?:doc|ext)_[A-Za-z0-9_.-]+)(?:\s*[,;，；、]\s*@?(?:doc|ext)_[A-Za-z0-9_.-]+)*)\s*\]"
)
_SOURCE_ID_IN_TAG_PATTERN = re.compile(r"@?((?:doc|ext)_[A-Za-z0-9_.-]+)")
_REFERENCE_HEADING_PATTERN = re.compile(r"^\s*(?:参考文献|references)\s*[:：]?\s*$", re.IGNORECASE)


class ChatService:
    """负责会话管理、证据上下文准备、模型调用和引用归一化的聊天服务。"""

    def __init__(
        self,
        session_repository: SessionRepository,
        library_repository: LibraryRepository,
        memory_service: MemoryService,
        retriever_service: RetrieverService,
        config_service: ConfigService | None = None,
        agent_orchestrator_service: AgentOrchestratorService | None = None,
    ) -> None:
        """初始化聊天服务并注入所需仓储和检索能力。"""
        self.session_repository = session_repository
        self.library_repository = library_repository
        self.memory_service = memory_service
        self.retriever_service = retriever_service
        self.config_service = config_service
        self.agent_orchestrator_service = agent_orchestrator_service

    def _to_json_safe(self, value: Any) -> Any:
        """把对象转换为可 JSON 序列化的结构。"""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if is_dataclass(value):
            return self._to_json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._to_json_safe(item) for item in value]
        if hasattr(value, "__dict__"):
            return self._to_json_safe(vars(value))
        return str(value)

    def create_session(self, title: str, user_goal: str, library_id: int | None = None) -> SessionRecord:
        """创建一个新会话，可选择绑定文献库。"""
        target_library_id = None
        if library_id is not None:
            target_library = self.library_repository.get_by_id(library_id)
            if target_library is None:
                raise ValueError(f"Library not found: {library_id}")
            target_library_id = target_library.id

        session_id = self.session_repository.create_session(
            title=title,
            user_goal=user_goal,
            library_id=target_library_id,
        )
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise RuntimeError("Failed to reload the session after creation.")
        return session

    def list_sessions(self) -> list[SessionRecord]:
        """返回全部会话列表。"""
        return self.session_repository.list_sessions()

    def list_messages(self, session_id: int) -> list[MessageRecord]:
        """返回指定会话的有序消息历史。"""
        return self.session_repository.list_messages(session_id)

    def rename_session(self, session_id: int, title: str) -> SessionRecord:
        """更新指定会话标题。"""
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
        """更新指定会话的置顶状态。"""
        updated = self.session_repository.update_session_pin_status(session_id, is_pinned)
        if not updated:
            raise ValueError(f"Session not found: {session_id}")
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        return session

    def bind_session_library(self, session_id: int, library_id: int) -> SessionRecord:
        """为未绑定文献库的会话绑定文献库；绑定后不允许改绑。"""
        session = self.session_repository.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

        if session.library_id is not None:
            if session.library_id == library.id:
                return session
            raise ValueError("Session already has a library and cannot be rebound.")

        updated = self.session_repository.update_session_library_id(session_id, library.id)
        reloaded_session = self.session_repository.get_session(session_id)
        if reloaded_session is None:
            raise ValueError(f"Session not found: {session_id}")
        if not updated and reloaded_session.library_id != library.id:
            raise ValueError("Session already has a library and cannot be rebound.")
        return reloaded_session

    def delete_session(self, session_id: int) -> None:
        """删除一个会话及其关联消息和记忆。"""
        deleted = self.session_repository.delete_session(session_id)
        if not deleted:
            raise ValueError(f"Session not found: {session_id}")

    def stream_chat(
        self,
        session_id: int,
        user_message: str,
        top_k: int = 5,
        allow_external_search: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """处理一次流式聊天请求。"""
        context: dict[str, Any] | None = None
        preparation: dict[str, Any] | None = None
        
        for agent_event in self.agent_orchestrator_service.stream_prepare_chat_context(
            session_id=session_id,
            user_message=user_message,
            top_k=top_k,
            external_search_only=False,
            allow_external_search=allow_external_search,
        ):
            if agent_event.type == "context_ready":
                if agent_event.context is None:
                    raise RuntimeError("Agent context was not attached to context_ready event.")
                context = self._build_context_from_orchestrated(
                    agent_event.context,
                    user_message=user_message,
                    allow_external_search=allow_external_search,
                )
                continue
            if agent_event.type == "prepare_start":
                preparation = self._start_preparation_record()
            elif agent_event.type == "prepare_step":
                preparation = self._record_preparation_step(preparation, agent_event.payload.get("step"))
            elif agent_event.type == "prepare_done":
                preparation = self._finish_preparation_record(
                    preparation,
                    agent_event.payload.get("elapsed_seconds"),
                )
            yield {"type": agent_event.type, **agent_event.payload}

        if context is None:
            raise RuntimeError("Failed to prepare chat context.")

        yield {
            "type": "meta",
            "session_id": session_id,
            "library_id": context["session"].library_id,
            "retrieved_memories": [self._memory_to_dict(memory) for memory in context["memories"]],
            "retrieved_documents": context["retrieved_docs"],
            "retrieval_mode": context.get("retrieval_mode"),
            "coverage": context.get("coverage"),
            "agent_actions": context.get("agent_actions", []),
            "pending_ingest": context.get("pending_ingest", []),
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
            orchestration=context.get("orchestration"),
            preparation=preparation,
        )
        yield {"type": "done", "answer": answer, "citations": citations}

    def _build_context_from_orchestrated(
        self,
        orchestrated_context: Any,
        *,
        user_message: str,
        allow_external_search: bool,
    ) -> dict[str, Any]:
        """把 agent 编排上下文转换为聊天模型可用的提示词上下文。"""
        prompt_payload = orchestrated_context.to_prompt_payload()
        history_context = self._format_recent_messages(self.session_repository.list_messages(orchestrated_context.session.id))
        memory_context = self._format_memories(prompt_payload["memories"])
        document_context = self._format_documents(prompt_payload["retrieved_docs"])

        prompt = self._build_orchestrated_prompt(
            session_goal=orchestrated_context.session.user_goal,
            library_name=orchestrated_context.library.name if orchestrated_context.library else "未绑定文献库",
            retrieval_mode=prompt_payload["retrieval_mode"],
            coverage=prompt_payload["coverage"],
            agent_actions=prompt_payload["agent_actions"],
            memory_context=memory_context,
            document_context=document_context,
            history_context=history_context,
            answer_task=user_message,
        )
        return {
            "session": orchestrated_context.session,
            "library": orchestrated_context.library,
            "memories": prompt_payload["memories"],
            "retrieved_docs": prompt_payload["retrieved_docs"],
            "prompt": prompt,
            "retrieval_mode": prompt_payload["retrieval_mode"],
            "coverage": prompt_payload["coverage"],
            "agent_actions": prompt_payload["agent_actions"],
            "pending_ingest": prompt_payload["pending_ingest"],
            "orchestration": prompt_payload,
        }


    def _build_orchestrated_prompt(
        self,
        *,
        session_goal: str,
        library_name: str,
        retrieval_mode: str,
        coverage: Any,
        agent_actions: Any,
        memory_context: str,
        document_context: str,
        history_context: str,
        answer_task: str,
    ) -> str:
        """构造用于最终回答模型的中文提示词。"""
        return f"""
你是论文助手 agent。请基于会话目标、历史消息、记忆、Agent 操作记录和候选文献证据，用中文严谨回答用户问题。

当前会话目标：
{session_goal}

当前文献库：
{library_name}

检索模式：
{retrieval_mode}

检索覆盖评估：
{coverage}

Agent 操作记录：
{agent_actions}

相关记忆：
{memory_context}

候选文献证据：
{document_context}

最近会话历史：
{history_context}

用户问题：
{answer_task}

请严格遵守以下要求：
1. 优先依据已提供的文献证据作答，不要脱离证据自由发挥。
2. 如果现有证据不足，请明确说明证据不足，不要编造出处。
3. 回答正文使用中文，表达准确、克制、学术化。
4. 如果检索模式为 no_library 且候选文献证据为“无”，可以基于通用知识回答，但不要伪造文献引用。
4. 如果需要引用文献，只能使用候选文献证据中给出的 source_id，并在正文中写成 [@source_id] 的形式。
5. 不要自行生成 [1]、[2] 这类编号；编号和参考文献表将由系统统一生成。
6. 同一篇文献多次引用时，必须复用同一个 source_id。
7. 如果需要在正文中引用多篇文献，使用','进行分隔，例如 [@source_id1, @source_id2] ，不要使用';'、' '、'-'、'，'等其他分隔符。
7. 不要输出“参考文献”标题，也不要自行在文末手写参考文献列表。
8. 不要引用未在候选文献证据中出现的 source_id。
9. 如果没有足够证据支持某个判断，请直接说明证据不足。
10. 请直接输出最终答案正文。
""".strip()


    def _persist_chat_result(
        self,
        *,
        session_id: int,
        user_message: str,
        answer: str,
        memories: list[MemoryRecord],
        retrieved_docs: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        orchestration: dict[str, Any] | None = None,
        preparation: dict[str, Any] | None = None,
    ) -> None:
        """持久化一轮用户消息和助手回复。"""
        retrieval_context = {
            "memories": [self._memory_to_dict(memory) for memory in memories],
            "documents": retrieved_docs,
            "citations": citations,
        }
        if orchestration:
            retrieval_context["orchestration"] = self._to_json_safe(orchestration)
        if preparation:
            retrieval_context["preparation"] = self._to_json_safe(preparation)
        self.session_repository.add_message(session_id, "user", user_message)
        self.session_repository.add_message(session_id, "assistant", answer, retrieval_context=retrieval_context)

    def _start_preparation_record(self) -> dict[str, Any]:
        """创建本轮流式回答的准备区内存记录，最终随 assistant 消息一次性入库。"""
        return {
            "status": "thinking",
            "elapsed_seconds": None,
            "steps": [],
        }

    def _record_preparation_step(self, preparation: dict[str, Any] | None, step: Any) -> dict[str, Any]:
        """把一条准备区进度事件合并到内存记录中。"""
        record = preparation or self._start_preparation_record()
        if not isinstance(step, dict):
            return record

        normalized_step = {
            "id": str(step.get("id") or step.get("query") or "external-query"),
            "status": str(step.get("status") or "running"),
            "source": str(step.get("source") or "arxiv"),
            "query": str(step.get("query") or ""),
            "sort_by": str(step.get("sort_by") or "relevance"),
            "sort_order": str(step.get("sort_order") or "descending"),
            "request_url": str(step.get("request_url") or ""),
            "result_count": step.get("result_count"),
            "error": str(step.get("error") or ""),
        }
        steps = record.setdefault("steps", [])
        if not isinstance(steps, list):
            record["steps"] = []
            steps = record["steps"]

        for index, existing_step in enumerate(steps):
            if isinstance(existing_step, dict) and existing_step.get("id") == normalized_step["id"]:
                steps[index] = {**existing_step, **normalized_step}
                break
        else:
            steps.append(normalized_step)
        return record

    def _finish_preparation_record(
        self,
        preparation: dict[str, Any] | None,
        elapsed_seconds: Any,
    ) -> dict[str, Any]:
        """标记准备区结束，并记录本轮准备阶段总耗时。"""
        record = preparation or self._start_preparation_record()
        record["status"] = "done"
        try:
            record["elapsed_seconds"] = float(elapsed_seconds)
        except (TypeError, ValueError):
            record["elapsed_seconds"] = 0.0
        return record

    def _build_source_id(self, document_id: int) -> str:
        """为本地文献构造 source_id。"""
        return f"doc_{document_id}"

    def _finalize_answer(self, raw_answer: str, retrieved_docs: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        """把模型输出中的 source_id 引用归一化为编号引用和引用绑定。"""
        body = self._strip_reference_section(raw_answer)
        ordered_bindings: list[dict[str, Any]] = []
        source_to_binding: dict[str, dict[str, Any]] = {}
        source_to_document = {
            str(document.get("source_id", "")): document
            for document in retrieved_docs
            if document.get("source_id")
        }

        def replace_tag(match: re.Match[str]) -> str:
            source_ids = _SOURCE_ID_IN_TAG_PATTERN.findall(match.group(1))
            reference_numbers: list[str] = []
            for source_id in source_ids:
                document = source_to_document.get(source_id)
                if document is None:
                    continue

                binding = source_to_binding.get(source_id)
                if binding is None:
                    binding = self._build_citation_binding(
                        number=len(ordered_bindings) + 1,
                        source_id=source_id,
                        document=document,
                    )
                    source_to_binding[source_id] = binding
                    ordered_bindings.append(binding)
                reference_numbers.append(str(binding["number"]))

            if not reference_numbers:
                return ""
            return f"[{','.join(reference_numbers)}]"

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
        """构造一条前端可直接使用的引用绑定记录。"""
        citation_text = self._format_citation_text(document)
        return {
            "number": number,
            "source_id": source_id,
            "document_id": document.get("document_id"),
            "text": citation_text,
            "title": document.get("title") or "",
            "abstract": document.get("abstract") or "",
            "file_path": document.get("file_path") or "",
            "authors": document.get("authors") or [],
            "year": document.get("year") or "",
            "venue": document.get("venue") or "",
            "doi": document.get("doi") or "",
            "url": document.get("url") or "",
            "citation_text_default": citation_text,
            "chunk_index": document.get("chunk_index"),
            "chunk_text": document.get("chunk_text") or "",
        }

    def _build_reference_section(self, citations: list[dict[str, Any]]) -> str:
        """渲染最终编号参考文献段落。"""
        lines: list[str] = []
        for citation in citations:
            number = citation.get("number")
            citation_text = self._format_citation_text(citation) or str(citation.get("text") or "").strip()
            if citation_text:
                lines.append(f"[{number}] {citation_text}")
        return "\n".join(lines)

    def _format_citation_text(self, payload: dict[str, Any]) -> str:
        """使用统一格式化器生成近似 GB/T 7714-2015 的引用文本。"""
        source_id = str(payload.get("source_id") or "")
        source_type = str(payload.get("source_type") or "")
        if not source_type and source_id.startswith("ext_"):
            source_type = "external"

        citation_text = format_gbt7714_citation(
            authors=payload.get("authors") or [],
            title=str(payload.get("title") or ""),
            year=str(payload.get("year") or ""),
            venue=str(payload.get("venue") or ""),
            doi=str(payload.get("doi") or ""),
            url=str(payload.get("url") or ""),
            source_type=source_type or "local",
        )
        return citation_text or str(payload.get("citation_text_default") or payload.get("title") or "").strip()

    def _strip_reference_section(self, answer: str) -> str:
        """移除模型自行生成的参考文献段落，后续由系统重建。"""
        lines = (answer or "").splitlines()
        heading_index = next(
            (index for index, line in enumerate(lines) if _REFERENCE_HEADING_PATTERN.match(line.strip())),
            -1,
        )
        if heading_index >= 0:
            return "\n".join(lines[:heading_index]).strip()
        return answer.strip()

    def _invoke_model(self, prompt: str) -> str:
        """执行一次非流式模型调用。"""
        response = self._build_model(streaming=False).invoke(prompt)
        return getattr(response, "content", str(response))

    def _build_model(self, *, streaming: bool) -> ChatTongyi:
        """根据当前运行时配置创建聊天模型实例。"""
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

    def _extract_stream_text(self, chunk: Any) -> str:
        """从流式模型 chunk 中提取可展示文本。"""
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
        """把较大的流式片段再切小，提升前端渐进显示体验。"""
        normalized_text = text.replace("\r\n", "\n")
        parts: list[str] = []
        current = ""

        for char in normalized_text:
            current += char
            if char in {"\n", "。", "，", "；", "：", ",", ".", "!", "?", ";", ":"} or len(current) >= max_chars:
                parts.append(current)
                current = ""

        if current:
            parts.append(current)
        return parts

    def _format_memories(self, memories: list[MemoryRecord]) -> str:
        """把召回记忆格式化为提示词片段。"""
        if not memories:
            return "无"
        return "\n".join(f"- [{memory.memory_type}] {memory.summary}: {memory.content}" for memory in memories)

    def _format_documents(self, documents: list[dict[str, Any]]) -> str:
        """把候选证据格式化为提示词片段。"""
        if not documents:
            return "无"

        lines: list[str] = []
        for item in documents:
            authors = ", ".join(item.get("authors", [])) or "未知"
            year = item.get("year") or "未知"
            venue = item.get("venue") or "未知"
            doi = item.get("doi") or "无"
            url = item.get("url") or "无"
            citation = self._format_citation_text(item) or "无"
            source_id = item.get("source_id")
            if not source_id and item.get("document_id") is not None:
                source_id = self._build_source_id(int(item["document_id"]))
            source_id = source_id or "unknown_source"
            lines.append(
                f"- 候选文献 source_id={source_id}\n"
                f"  标题: {item.get('title') or '未知'}\n"
                f"  作者: {authors}\n"
                f"  年份: {year}\n"
                f"  来源: {venue}\n"
                f"  DOI: {doi}\n"
                f"  URL: {url}\n"
                f"  默认引用文本: {citation}\n"
                f"  若在正文中引用该文献，请写成 [@{source_id}]\n"
                f"  摘要: {item.get('abstract') or '无'}\n"
                f"  证据片段: {item.get('chunk_text') or '无'}"
            )
        return "\n".join(lines)

    def _format_recent_messages(self, messages: list[MessageRecord], limit: int = 6) -> str:
        """格式化最近若干轮会话作为短期上下文。"""
        recent = messages[-limit:]
        if not recent:
            return "无"
        return "\n".join(f"{message.role}: {message.content}" for message in recent)

    def _memory_to_dict(self, memory: MemoryRecord) -> dict[str, Any]:
        """把记忆记录转换为可 JSON 序列化的字典。"""
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
