from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
from app_backend.models import ParsedDocument
from app_backend.services.config_service import ConfigService
from app_backend.services.llm_concurrency_limiter import LLMConcurrencyLimiter


_JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")
_FIGURE_OR_TABLE_PATTERN = re.compile(
    r"^\s*(?:fig\.?|figure|table|图|表)\s*[\dIVXLC一二三四五六七八九十]*",
    re.IGNORECASE,
)
_SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(?:abstract|摘要|references|参考文献|appendix|附录|"
    r"(?:[IVXLC]+|\d+)(?:[.\s、]|$))",
    re.IGNORECASE,
)
_NOISE_ANCHOR_PATTERN = re.compile(
    r"(?:authorized licensed use|downloaded on|restrictions apply|"
    r"vol\.\s*\d+|transactions on|et al\.:)",
    re.IGNORECASE,
)


@dataclass
class _LocatedSection:
    """语义分块内部使用的已定位章节结构。"""

    section_type: str
    title: str
    start_anchor: str
    indexable: bool
    start_char: int
    end_char: int
    text: str
    batch_index: int
    page_start: int
    page_end: int


class SemanticChunkService:
    """基于 LLM 结构识别和程序切块的语义分块服务。"""

    def __init__(
        self,
        config_service: ConfigService,
        llm_limiter: LLMConcurrencyLimiter,
        chunk_overlap: int = 150,
    ) -> None:
        """初始化语义分块服务。"""
        self.config_service = config_service
        self.llm_limiter = llm_limiter
        self.base_chunk_overlap = max(0, chunk_overlap)

    def split_document(self, parsed_document: ParsedDocument, *, library_id: int) -> list[dict[str, Any]]:
        """对一篇解析后的 PDF 执行语义分块，并返回可写入向量库的文本块。"""
        source_text = parsed_document.raw_text.strip()
        if not source_text:
            return []

        page_texts = parsed_document.page_texts or [source_text]
        page_spans = self._build_page_spans(page_texts, max_chars=len(source_text))
        page_batches = self._build_page_batches(
            page_spans=page_spans,
            source_text=source_text,
            pages_per_batch=config.SEMANTIC_CHUNK_PAGES_PER_BATCH,
        )
        if not page_batches:
            return self._build_recursive_chunk_payloads(source_text, library_id=library_id)

        sections = self._identify_sections_in_parallel(page_batches)
        located_sections = self._locate_batched_sections(source_text, sections)
        located_sections = self._merge_adjacent_same_sections(located_sections)
        chunks = self._chunk_sections_programmatically(located_sections, library_id=library_id)

        if chunks:
            return chunks
        return self._build_recursive_chunk_payloads(source_text, library_id=library_id)

    def _identify_sections_in_parallel(self, page_batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """并发识别每个页组中的章节结构。"""
        prompt = self._build_structure_prompt()
        sections: list[dict[str, Any]] = []
        max_workers = min(
            max(1, config.SEMANTIC_CHUNK_MAX_WORKERS_PER_DOCUMENT),
            len(page_batches),
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(self._invoke_structure_prompt, prompt, batch, len(page_batches)): batch
                for batch in page_batches
            }
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                raw_payload = future.result()
                payload = self._parse_json_payload(raw_payload)
                batch_sections = self._normalize_sections(payload.get("sections"))
                for section in batch_sections:
                    section.update(
                        {
                            "batch_index": batch["batch_index"],
                            "page_start": batch["page_start"],
                            "page_end": batch["page_end"],
                            "batch_start_char": batch["start_char"],
                            "batch_end_char": batch["end_char"],
                        }
                    )
                    if self._is_valid_section(section):
                        sections.append(section)

        sections.sort(key=lambda item: (item.get("batch_index", 0), item.get("order", 0)))
        return sections

    def _build_structure_prompt(self) -> ChatPromptTemplate:
        """构造语义结构识别提示词。"""
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是论文结构识别助手。你的任务是识别当前页组中出现的论文主要结构，"
                    "只允许输出 JSON，不要输出解释、Markdown 或额外文本。"
                    "如果当前页组只是上一节内容的延续，且没有新的明确小节标题，"
                    "可以返回空 sections。"
                    "只识别论文主章节或一级章节标题，例如 Abstract、I. INTRODUCTION、"
                    "II.、III. 等等，或者1.、2.、3. 等等。"
                    "不要把 Fig/Figure/图、Table/表、页眉、页码、作者名、期刊名、"
                    "下载授权提示识别为 section。"
                    "不要为了页组开头强行创建 section；如果页组开头是上一节延续，"
                    "应等待出现新的主章节标题后再输出 section。"
                    "JSON 格式必须严格如下："
                    "{{\"sections\": [{{"
                    "\"section_type\": str, \"title\": str, "
                    "\"start_anchor\": str, \"indexable\": bool"
                    "}}]}}。"
                    "section_type 使用：abstract, toc, introduction, related_work, method, "
                    "experiment, result, discussion, conclusion, references, appendix, other。"
                    "如果识别到参考文献区，请单独输出 references 段，并将 indexable 设为 false。"
                    "如果识别到目录页，请单独输出 toc 段，并将 indexable 设为 false。"
                    "title 和 start_anchor 必须尽量复制原文中该部分开头的标题或首句短语，"
                    "title 为章节给简短标题，例如 Abstract、I. INTRODUCTION，不包括 Fig/Figure、Table、页眉。"
                    "start_anchor 为章节标题和开头句子，便于程序回原文定位，例如Abstract— With the increasing railway、I. INTRODUCTION\nOn major rail lines during peak hours。"
                    "sections 必须按出现顺序排列。"
                    ,
                ),
                (
                    "human",
                    "当前输入是全文的第 {batch_index}/{batch_count} 个页组，"
                    "页码范围：{page_start}-{page_end}，页组正文长度：{text_length} 字符。\n\n"
                    "以下是待识别结构的页组正文：\n{text}\n\n请直接输出 JSON。",
                ),
            ]
        )

    def _invoke_structure_prompt(
        self,
        prompt: ChatPromptTemplate,
        batch: dict[str, Any],
        batch_count: int,
    ) -> str:
        """调用 LLM 识别一个页组内的章节结构。"""
        chain = prompt | self._build_model() | StrOutputParser()
        payload = {
            "text": batch["text"],
            "batch_index": batch["batch_index"],
            "batch_count": batch_count,
            "page_start": batch["page_start"],
            "page_end": batch["page_end"],
            "text_length": len(batch["text"]),
        }
        return self.llm_limiter.run(lambda: chain.invoke(payload)).strip()

    def _build_model(self) -> ChatTongyi:
        """根据运行时配置构建 LLM。"""
        return ChatTongyi(
            model=self.config_service.get_llm_model_name(),
            api_key=self.config_service.get_api_key() or None,
        )

    def _parse_json_payload(self, raw: str) -> dict[str, Any]:
        """从模型输出中解析 JSON 对象。"""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = _JSON_OBJECT_PATTERN.search(raw)
            if not match:
                raise
            return json.loads(match.group(0))

    def _normalize_sections(self, payload: object) -> list[dict[str, Any]]:
        """规范化模型返回的章节列表。"""
        if not isinstance(payload, list):
            return []

        sections: list[dict[str, Any]] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            title = self._clean_inline_text(item.get("title"))
            start_anchor = self._clean_inline_text(item.get("start_anchor")) or title
            if not start_anchor:
                continue
            sections.append(
                {
                    "order": index,
                    "section_type": self._clean_inline_text(item.get("section_type")) or "other",
                    "title": title or f"section_{index}",
                    "start_anchor": start_anchor,
                    "indexable": self._to_bool(item.get("indexable"), default=True),
                }
            )
        return sections

    def _is_valid_section(self, section: dict[str, Any]) -> bool:
        """过滤图注、表注、页眉等不应成为章节边界的伪 section。"""
        title = self._clean_inline_text(section.get("title"))
        anchor = self._clean_inline_text(section.get("start_anchor"))
        if _FIGURE_OR_TABLE_PATTERN.search(title) or _FIGURE_OR_TABLE_PATTERN.search(anchor):
            return False
        if _NOISE_ANCHOR_PATTERN.search(anchor) and not _SECTION_HEADING_PATTERN.search(anchor):
            return False
        if len(title) > 120 and not _SECTION_HEADING_PATTERN.search(title):
            return False
        return True

    def _build_page_spans(self, page_texts: list[str], *, max_chars: int) -> list[dict[str, Any]]:
        """将每页文本映射回全文字符区间。"""
        spans: list[dict[str, Any]] = []
        offset = 0
        has_previous_text = False
        for page_index, page_text in enumerate(page_texts, start=1):
            cleaned_text = page_text.strip()
            if not cleaned_text:
                continue
            if has_previous_text:
                offset += 2
            start_char = offset
            end_char = start_char + len(cleaned_text)
            offset = end_char
            has_previous_text = True
            if start_char >= max_chars:
                break
            spans.append(
                {
                    "page_number": page_index,
                    "start_char": start_char,
                    "end_char": min(end_char, max_chars),
                }
            )
            if end_char >= max_chars:
                break
        return spans

    def _build_page_batches(
        self,
        *,
        page_spans: list[dict[str, Any]],
        source_text: str,
        pages_per_batch: int,
    ) -> list[dict[str, Any]]:
        """按固定页数构造结构识别页组。"""
        batches: list[dict[str, Any]] = []
        pages_per_batch = max(1, pages_per_batch)
        for start_index in range(0, len(page_spans), pages_per_batch):
            span_group = page_spans[start_index:start_index + pages_per_batch]
            if not span_group:
                continue
            start_char = span_group[0]["start_char"]
            end_char = span_group[-1]["end_char"]
            batch_text = source_text[start_char:end_char].strip()
            if not batch_text:
                continue
            batches.append(
                {
                    "batch_index": len(batches) + 1,
                    "page_start": span_group[0]["page_number"],
                    "page_end": span_group[-1]["page_number"],
                    "start_char": start_char,
                    "end_char": end_char,
                    "text": batch_text,
                }
            )
        return batches

    def _locate_batched_sections(
        self,
        source_text: str,
        sections: list[dict[str, Any]],
    ) -> list[_LocatedSection]:
        """优先在页组范围内定位 section 起点。"""
        located: list[dict[str, Any]] = []
        seen_positions: set[tuple[int, str, str]] = set()
        for section in sections:
            batch_start = max(0, min(int(section.get("batch_start_char") or 0), len(source_text)))
            batch_end = max(batch_start, min(int(section.get("batch_end_char") or len(source_text)), len(source_text)))
            batch_text = source_text[batch_start:batch_end]
            local_start = self._find_anchor(batch_text, section["start_anchor"], start_at=0)
            if local_start < 0:
                global_start = self._find_anchor(source_text, section["start_anchor"], start_at=batch_start)
                if global_start < 0 or global_start > batch_end:
                    continue
                start_char = global_start
            else:
                start_char = batch_start + local_start

            dedupe_key = (start_char, section["section_type"], section["title"])
            if dedupe_key in seen_positions:
                continue
            seen_positions.add(dedupe_key)
            located.append({**section, "start_char": start_char})

        located.sort(key=lambda item: item["start_char"])
        results: list[_LocatedSection] = []
        for index, section in enumerate(located):
            end_char = located[index + 1]["start_char"] if index + 1 < len(located) else len(source_text)
            text = source_text[section["start_char"]:end_char].strip()
            if not text:
                continue
            results.append(
                _LocatedSection(
                    section_type=section["section_type"],
                    title=section["title"],
                    start_anchor=section["start_anchor"],
                    indexable=section["indexable"],
                    start_char=section["start_char"],
                    end_char=end_char,
                    text=text,
                    batch_index=int(section.get("batch_index") or 0),
                    page_start=int(section.get("page_start") or 0),
                    page_end=int(section.get("page_end") or 0),
                )
            )
        return results

    def _merge_adjacent_same_sections(self, sections: list[_LocatedSection]) -> list[_LocatedSection]:
        """合并跨页组产生的相邻同章节。"""
        merged_sections: list[_LocatedSection] = []
        for section in sections:
            if not merged_sections:
                merged_sections.append(section)
                continue
            previous = merged_sections[-1]
            can_merge = (
                previous.section_type == section.section_type
                and self._normalize_section_title(previous.title) == self._normalize_section_title(section.title)
                and previous.indexable == section.indexable
            )
            if not can_merge:
                merged_sections.append(section)
                continue
            previous.end_char = section.end_char
            previous.text = f"{previous.text.rstrip()}\n\n{section.text.lstrip()}".strip()
            previous.page_end = section.page_end
        return merged_sections

    def _chunk_sections_programmatically(
        self,
        sections: list[_LocatedSection],
        *,
        library_id: int,
    ) -> list[dict[str, Any]]:
        """对已定位章节执行程序切块，并跳过不可索引章节。"""
        chunks: list[dict[str, Any]] = []
        for section in sections:
            if not section.indexable:
                continue
            section_chunks = self._split_text_with_recursive_splitter(section.text, library_id=library_id)
            for chunk_text in section_chunks:
                cleaned_chunk = chunk_text.strip()
                if cleaned_chunk:
                    chunks.append(
                        {
                            "section_type": section.section_type,
                            "section_title": section.title,
                            "section_chunk_index": len(chunks),
                            "indexable": section.indexable,
                            "chunk_text": cleaned_chunk,
                        }
                    )
        merged_chunks = self._merge_adjacent_compatible_chunks(chunks, library_id=library_id)
        return self._renumber_section_chunk_indexes(merged_chunks)

    def _merge_adjacent_compatible_chunks(
        self,
        chunks: list[dict[str, Any]],
        *,
        library_id: int,
    ) -> list[dict[str, Any]]:
        """合并相邻且类型一致的短 chunk，减少碎片化。"""
        merged_chunks: list[dict[str, Any]] = []
        chunk_size = self._get_chunk_size(library_id)
        for chunk in chunks:
            if not merged_chunks:
                merged_chunks.append(dict(chunk))
                continue
            previous = merged_chunks[-1]
            merged_text = f"{previous['chunk_text']}\n\n{chunk['chunk_text']}"
            can_merge = (
                previous.get("section_type") == chunk.get("section_type")
                and previous.get("section_title") == chunk.get("section_title")
                and previous.get("indexable") == chunk.get("indexable")
                and len(merged_text) <= chunk_size
            )
            if can_merge:
                previous["chunk_text"] = merged_text
            else:
                merged_chunks.append(dict(chunk))
        return merged_chunks

    def _build_recursive_chunk_payloads(
        self,
        text: str,
        *,
        library_id: int,
    ) -> list[dict[str, Any]]:
        """将递归分块结果包装成统一的结构化 chunk。"""
        chunks = self._split_text_with_recursive_splitter(text, library_id=library_id)
        return [
            {
                "section_type": "recursive",
                "section_title": "",
                "section_chunk_index": index,
                "indexable": True,
                "chunk_text": chunk_text,
            }
            for index, chunk_text in enumerate(chunks)
        ]

    def _renumber_section_chunk_indexes(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按章节重新编号 section_chunk_index，确保合并后编号连续。"""
        counters: dict[tuple[str, str], int] = {}
        for chunk in chunks:
            key = (
                str(chunk.get("section_type") or ""),
                str(chunk.get("section_title") or ""),
            )
            chunk["section_chunk_index"] = counters.get(key, 0)
            counters[key] = int(chunk["section_chunk_index"]) + 1
        return chunks

    def _split_text_with_recursive_splitter(self, text: str, *, library_id: int) -> list[str]:
        """在章节内部使用递归分割器兜底切块。"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._get_chunk_size(library_id),
            chunk_overlap=self._get_chunk_overlap(library_id),
            keep_separator=True,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                ". ",
                "! ",
                "? ",
                "; ",
                " ",
                "",
            ],
            length_function=len,
            is_separator_regex=False,
        )
        return [chunk.strip() for chunk in splitter.split_text(text.strip()) if chunk.strip()]

    def _get_chunk_size(self, library_id: int) -> int:
        """读取当前文献库的 chunk 大小。"""
        return max(1, self.config_service.get_embedding_max_input_tokens(library_id))

    def _get_chunk_overlap(self, library_id: int) -> int:
        """根据 chunk 大小裁剪重叠长度。"""
        chunk_size = self._get_chunk_size(library_id)
        return min(self.base_chunk_overlap, max(0, chunk_size - 1))

    def _find_anchor(self, text: str, anchor: str, *, start_at: int = 0) -> int:
        """尽量在文本中定位模型返回的起始锚点。"""
        candidate = anchor.strip()
        if not candidate:
            return -1
        direct_index = text.find(candidate, start_at)
        if direct_index >= 0:
            return direct_index
        whitespace_pattern = r"\s+".join(re.escape(part) for part in candidate.split())
        if whitespace_pattern:
            match = re.search(whitespace_pattern, text[start_at:], flags=re.IGNORECASE)
            if match:
                return start_at + match.start()
        fallback = candidate[: min(30, len(candidate))].strip()
        if fallback:
            fallback_pattern = r"\s+".join(re.escape(part) for part in fallback.split())
            if fallback_pattern:
                match = re.search(fallback_pattern, text[start_at:], flags=re.IGNORECASE)
                if match:
                    return start_at + match.start()
        return -1

    def _normalize_section_title(self, value: object) -> str:
        """规范化章节标题，用于判断是否属于同一章节。"""
        return self._clean_inline_text(value).lower()

    @staticmethod
    def _clean_inline_text(value: object) -> str:
        """清理单行文本字段。"""
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    @staticmethod
    def _to_bool(value: object, *, default: bool) -> bool:
        """把模型输出尽量转换成布尔值。"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1", "y"}:
                return True
            if lowered in {"false", "no", "0", "n"}:
                return False
        return default
