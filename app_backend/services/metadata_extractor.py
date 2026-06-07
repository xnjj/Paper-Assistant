from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime

from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app_backend.models import ExtractedMetadata, ParsedDocument
from app_backend.services.citation_formatter import format_gbt7714_citation
from app_backend.services.config_service import ConfigService
from app_backend.services.llm_concurrency_limiter import LLMConcurrencyLimiter

logger = logging.getLogger(__name__)

_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_URL_PATTERN = re.compile(r"https?://[^\s<>)\]}]+", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
_JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")
_ABSTRACT_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:abstract|摘要)\s*[:：]?\s*(.+?)(?=(?:\n\s*(?:keywords?|keyword|关键词)\s*[:：]?)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_ABSTRACT_LINE_PATTERN = re.compile(r"^\s*(?:abstract|摘要)\b", re.IGNORECASE)
_KEYWORDS_LINE_PATTERN = re.compile(r"^\s*(?:keywords?|keyword|关键词)\s*[:：]?", re.IGNORECASE)
_AUTHOR_SPLIT_PATTERN = re.compile(r"\s*(?:,|，|、|;|；| and | AND )\s*")
_KEYWORD_SPLIT_PATTERN = re.compile(r"\s*(?:,|，|、|;|；|/|\|)\s*")
_ENGLISH_NAME_PATTERN = re.compile(r"[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){0,3}")
_CHINESE_NAME_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,4}")

_AFFILIATION_HINTS = (
    "university",
    "college",
    "school",
    "department",
    "institute",
    "laboratory",
    "lab",
    "academy",
    "correspondence",
    "research center",
    "email",
    "工程",
    "学院",
    "大学",
    "研究所",
    "实验室",
    "通信作者",
    "作者单位",
)
_VENUE_HINTS = (
    "journal",
    "transactions",
    "proceedings",
    "conference",
    "symposium",
    "letters",
    "ieee",
    "acm",
    "springer",
    "elsevier",
    "arxiv",
    "学报",
    "期刊",
    "会议",
    "大学学报",
    "交通运输",
    "铁道",
)
_TITLE_BLOCK_LIMIT = 10
_YEAR_MIN = 1990
_YEAR_MAX = datetime.now().year + 1


class MetadataExtractorService:
    """论文元数据抽取服务。

    当前实现采用三段式策略：
    1. 先做规则抽取，拿到 DOI、年份、关键词、作者等稳定提示。
    2. 再调用模型做补全，减少 PDF 文本噪声带来的遗漏。
    3. 最后统一做字段规范化，并生成默认引用格式。
    """

    def __init__(
        self,
        config_service: ConfigService | None = None,
        llm_limiter: LLMConcurrencyLimiter | None = None,
    ) -> None:
        """初始化元数据抽取服务。"""
        self.config_service = config_service
        self.llm_limiter = llm_limiter

    def extract(self, parsed_document: ParsedDocument) -> ExtractedMetadata:
        """从解析后的 PDF 中抽取结构化元数据。

        Args:
            parsed_document: PDF 解析层输出，包含全文和摘要优先文本。

        Returns:
            ExtractedMetadata: 规范化后的元数据对象。
        """
        rule_hints = self._extract_rule_hints(parsed_document)
        payload: dict[str, object] = {}

        try:
            payload = self._extract_with_llm(parsed_document, rule_hints)
        except Exception as exc:
            logger.warning("元数据抽取回退到规则结果：%s", exc)

        return self._build_metadata(
            file_name=parsed_document.file_name,
            payload=payload,
            rule_hints=rule_hints,
        )

    def _extract_with_llm(
        self,
        parsed_document: ParsedDocument,
        rule_hints: dict[str, object],
    ) -> dict[str, object]:
        """调用模型补全文献元数据。

        这里仍然保留英文 JSON 字段名，便于与数据库字段直接映射；
        但系统提示和用户提示都改成中文，减少中文论文抽取时的偏差。
        """
        text_for_llm = (
            parsed_document.abstract_priority_text.strip() or parsed_document.raw_text
        )[:18000]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是论文元数据抽取助手。"
                    "请根据给定的论文文本与规则提示，提取最终元数据。"
                    "只输出 JSON，不要输出解释、前后缀或 Markdown。"
                    "JSON 的字段必须严格使用以下英文字段名："
                    "{{\"title\": str, \"abstract\": str, \"keywords\": [str], "
                    "\"authors\": [str], \"year\": str, \"doi\": str, "
                    "\"url\": str, \"venue\": str, \"language\": str, "
                    "\"publication_date\": str, \"document_type\": str, "
                    "\"publisher\": str, \"publisher_place\": str, "
                    "\"volume\": str, \"issue\": str, \"pages\": str, "
                    "\"article_number\": str, \"degree_institution\": str, "
                    "\"degree_location\": str, \"proceedings_title\": str, "
                    "\"conference_name\": str, \"extra_metadata\": object}}。"
                    "其中 authors 必须是作者姓名列表，不能写作者单位。"
                    "document_type 只能优先使用 J、J/OL、C、D、M、R、EB/OL 等 GB/T 类型标识。"
                    "keywords 必须尽量从论文中提取，如果出现“关键词”或“Keywords”字段，优先使用它。"
                    "未知字段请返回空字符串或空数组。",
                ),
                (
                    "human",
                    "下面是根据 PDF 规则初步提取出的提示信息：\n"
                    "{rule_hints}\n\n"
                    "请结合这些提示和以下论文文本，输出最终元数据 JSON：\n\n"
                    "{text}",
                ),
            ]
        )

        chain = prompt | self._build_model() | StrOutputParser()
        payload = {
            "text": text_for_llm,
            "rule_hints": json.dumps(rule_hints, ensure_ascii=False),
        }
        if self.llm_limiter is not None:
            raw = self.llm_limiter.run(lambda: chain.invoke(payload)).strip()
        else:
            raw = chain.invoke(payload).strip()
        return self._parse_json_payload(raw)

    def _build_model(self) -> ChatTongyi:
        """Build one model instance from the active runtime config."""
        if self.config_service is None:
            raise ValueError("模型配置服务未初始化，请先完成模型配置。")
        model_name = self.config_service.get_llm_model_name()
        api_key = self.config_service.get_api_key()

        return ChatTongyi(
            model=model_name,
            api_key=api_key or None,
        )

    def _build_metadata(
        self,
        *,
        file_name: str,
        payload: dict[str, object],
        rule_hints: dict[str, object],
    ) -> ExtractedMetadata:
        """合并模型输出与规则提示，得到最终元数据。"""
        title = (
            self._clean_text(payload.get("title"))
            or self._clean_text(rule_hints.get("title"))
            or PathFallback.name_without_suffix(file_name)
        )
        abstract = (
            self._clean_text(payload.get("abstract"))
            or self._clean_text(rule_hints.get("abstract"))
            or "（未提取到摘要）"
        )
        keywords = self._normalize_keywords(payload.get("keywords"))
        if not keywords:
            keywords = self._normalize_keywords(rule_hints.get("keywords"))

        authors = self._normalize_authors(payload.get("authors"))
        if not authors:
            authors = list(rule_hints.get("authors", []))

        year = self._normalize_year(payload.get("year")) or str(rule_hints.get("year", ""))
        doi = self._normalize_doi(payload.get("doi")) or str(rule_hints.get("doi", ""))
        url = self._normalize_url(payload.get("url")) or str(rule_hints.get("url", ""))
        venue = (
            self._clean_text(payload.get("venue"))
            or self._clean_text(rule_hints.get("venue"))
            or ""
        )
        language = self._normalize_language(payload.get("language"), title, abstract)
        publication_date = self._normalize_date(payload.get("publication_date")) or str(rule_hints.get("publication_date", ""))
        document_type = (
            self._normalize_document_type(payload.get("document_type"))
            or self._normalize_document_type(rule_hints.get("document_type"))
            or self._infer_document_type(title=title, venue=venue, url=url)
        )
        publisher = self._clean_text(payload.get("publisher"))
        publisher_place = self._clean_text(payload.get("publisher_place"))
        volume = self._clean_text(payload.get("volume"))
        issue = self._clean_text(payload.get("issue"))
        pages = self._normalize_pages(payload.get("pages"))
        article_number = self._clean_text(payload.get("article_number"))
        degree_institution = self._clean_text(payload.get("degree_institution"))
        degree_location = self._clean_text(payload.get("degree_location"))
        proceedings_title = self._clean_text(payload.get("proceedings_title"))
        conference_name = self._clean_text(payload.get("conference_name"))
        extra_metadata = self._normalize_extra_metadata(payload.get("extra_metadata"))

        if doi and not url:
            url = f"https://doi.org/{doi}"

        citation_text_default = self._build_default_citation(
            authors=authors,
            title=title,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            publication_date=publication_date,
            document_type=document_type,
            publisher=publisher,
            publisher_place=publisher_place,
            volume=volume,
            issue=issue,
            pages=pages,
            article_number=article_number,
            degree_institution=degree_institution,
            degree_location=degree_location,
            proceedings_title=proceedings_title,
            conference_name=conference_name,
        )

        return ExtractedMetadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            authors=authors,
            year=year,
            doi=doi,
            url=url,
            venue=venue,
            citation_text_default=citation_text_default,
            language=language,
            publication_date=publication_date,
            document_type=document_type,
            publisher=publisher,
            publisher_place=publisher_place,
            volume=volume,
            issue=issue,
            pages=pages,
            article_number=article_number,
            degree_institution=degree_institution,
            degree_location=degree_location,
            proceedings_title=proceedings_title,
            conference_name=conference_name,
            extra_metadata=extra_metadata,
        )

    def _extract_rule_hints(self, parsed_document: ParsedDocument) -> dict[str, object]:
        """提取规则层提示信息。

        你提到的 `keywords` 丢失问题，之前确实可能发生：
        - 旧逻辑没有从规则层抽取 `keywords`
        - `_build_metadata()` 只采用模型返回的 `keywords`
        - 一旦模型漏掉该字段，数据库里就会落空数组

        现在这里增加了关键词规则抽取，并在最终合并时作为兜底。
        """
        priority_text = parsed_document.abstract_priority_text.strip() or parsed_document.raw_text
        lines = self._normalize_lines(priority_text)
        abstract_index = self._find_abstract_index(lines)
        doi = self._extract_doi(priority_text) or self._extract_doi(parsed_document.raw_text)
        url = self._extract_url(priority_text) or self._extract_url(parsed_document.raw_text)

        venue = self._extract_venue_hint(lines)
        return {
            "title": self._extract_title_hint(lines),
            "abstract": self._extract_abstract_hint(priority_text),
            "keywords": self._extract_keywords_hint(lines),
            "authors": self._extract_author_hint(lines, abstract_index),
            "year": self._extract_year_hint(priority_text, lines),
            "doi": doi,
            "url": url or (f"https://doi.org/{doi}" if doi else ""),
            "venue": venue,
            "document_type": self._infer_document_type(
                title=self._extract_title_hint(lines),
                venue=venue,
                url=url,
            ),
        }

    def _normalize_lines(self, text: str) -> list[str]:
        """把原始文本整理成去空行的干净行列表。"""
        lines: list[str] = []
        for raw_line in text.splitlines():
            cleaned = self._clean_text(raw_line)
            if cleaned:
                lines.append(cleaned)
        return lines

    def _find_abstract_index(self, lines: list[str]) -> int:
        """定位摘要所在行，用于缩小作者行搜索范围。"""
        for index, line in enumerate(lines):
            if _ABSTRACT_LINE_PATTERN.search(line):
                return index
        return min(len(lines), 12)

    def _extract_title_hint(self, lines: list[str]) -> str:
        """从开头几行中选择最像标题的一行。"""
        candidates: list[str] = []
        for line in lines[:_TITLE_BLOCK_LIMIT]:
            lowered = line.lower()
            if (
                _ABSTRACT_LINE_PATTERN.search(line)
                or _KEYWORDS_LINE_PATTERN.search(line)
                or "doi" in lowered
                or "http://" in lowered
                or "https://" in lowered
                or "@" in line
                or self._looks_like_affiliation(line)
                or len(line) < 8
            ):
                continue
            candidates.append(line)

        if not candidates:
            return ""
        return max(candidates, key=len)

    def _extract_abstract_hint(self, text: str) -> str:
        """从摘要段中提取摘要内容。"""
        match = _ABSTRACT_PATTERN.search(text)
        if not match:
            return ""
        abstract = self._clean_text(match.group(1))
        return abstract[:3000]

    def _extract_keywords_hint(self, lines: list[str]) -> list[str]:
        """从“关键词/Keywords”行中提取关键词。

        这里先找带关键词标识的行，优先取冒号后的内容；
        如果该行只有“关键词：”而内容在下一行，也会继续读取下一行。
        """
        for index, line in enumerate(lines):
            if not _KEYWORDS_LINE_PATTERN.search(line):
                continue

            suffix = _KEYWORDS_LINE_PATTERN.sub("", line, count=1).strip(" :：")
            if not suffix and index + 1 < len(lines):
                next_line = lines[index + 1]
                if not _ABSTRACT_LINE_PATTERN.search(next_line):
                    suffix = next_line.strip(" :：")

            if suffix:
                return self._normalize_keywords(_KEYWORD_SPLIT_PATTERN.split(suffix))

        return []

    def _extract_author_hint(self, lines: list[str], abstract_index: int) -> list[str]:
        """尝试从标题区与摘要区之间提取作者姓名。"""
        search_lines = lines[1:abstract_index]
        for line in search_lines[:8]:
            if (
                len(line) > 120
                or "@" in line
                or self._looks_like_affiliation(line)
                or _YEAR_PATTERN.search(line)
            ):
                continue

            names = self._split_author_line(line)
            if 1 <= len(names) <= 10:
                return names
        return []

    def _extract_year_hint(self, text: str, lines: list[str]) -> str:
        """从页眉附近优先提取年份，不足时再回退到全文统计。"""
        for line in lines[:20]:
            year = self._first_valid_year(_YEAR_PATTERN.findall(line))
            if year:
                return year

        all_years = [match for match in _YEAR_PATTERN.findall(text) if self._is_valid_year(match)]
        if not all_years:
            return ""
        return Counter(all_years).most_common(1)[0][0]

    def _extract_doi(self, text: str) -> str:
        """提取文本中的第一个 DOI。"""
        match = _DOI_PATTERN.search(text)
        return match.group(0).rstrip(".,);]") if match else ""

    def _extract_url(self, text: str) -> str:
        """提取文本中的第一个有效链接。"""
        for match in _URL_PATTERN.finditer(text):
            url = match.group(0).rstrip(".,);]")
            if "orcid.org" in url.lower():
                continue
            return url
        return ""

    def _extract_venue_hint(self, lines: list[str]) -> str:
        """从前几行里提取期刊名或会议信息。"""
        for line in lines[:40]:
            lowered = line.lower()
            if any(keyword in lowered for keyword in _VENUE_HINTS):
                return line[:240]
        return ""

    def _split_author_line(self, line: str) -> list[str]:
        """把疑似作者行切成作者姓名列表。"""
        normalized = re.sub(r"[*†‡§]+", " ", line)
        normalized = re.sub(r"\b\d+\b", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        if any(separator in normalized for separator in [",", "，", "、", ";", "；", " and ", " AND "]):
            candidates = _AUTHOR_SPLIT_PATTERN.split(normalized)
            names = [self._clean_person_name(candidate) for candidate in candidates]
            names = [name for name in names if self._is_person_name(name)]
            if names:
                return self._deduplicate_preserve_order(names)

        english_names = [self._clean_person_name(name) for name in _ENGLISH_NAME_PATTERN.findall(normalized)]
        english_names = [name for name in english_names if self._is_person_name(name)]
        if len(english_names) >= 2:
            return self._deduplicate_preserve_order(english_names)

        chinese_names = [self._clean_person_name(name) for name in _CHINESE_NAME_PATTERN.findall(normalized)]
        chinese_names = [name for name in chinese_names if self._is_person_name(name)]
        if 1 <= len(chinese_names) <= 10 and len(normalized) <= 40:
            return self._deduplicate_preserve_order(chinese_names)

        return []

    def _parse_json_payload(self, raw: str) -> dict[str, object]:
        """从模型响应中提取第一个 JSON 对象。"""
        match = _JSON_OBJECT_PATTERN.search(raw)
        if not match:
            raise ValueError("元数据抽取模型没有返回 JSON。")
        payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("元数据抽取模型返回的不是 JSON 对象。")
        return payload

    def _normalize_keywords(self, keywords: object) -> list[str]:
        """清洗并去重关键词列表。"""
        if isinstance(keywords, str):
            keywords = _KEYWORD_SPLIT_PATTERN.split(keywords)
        if not isinstance(keywords, list):
            return []

        cleaned_keywords: list[str] = []
        seen = set()
        for keyword in keywords:
            cleaned = self._clean_text(keyword).strip(" ,;，；")
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned_keywords.append(cleaned)
            if len(cleaned_keywords) >= 10:
                break
        return cleaned_keywords

    def _normalize_authors(self, authors: object) -> list[str]:
        """清洗并去重模型返回的作者列表。"""
        if isinstance(authors, str):
            authors = _AUTHOR_SPLIT_PATTERN.split(authors)
        if not isinstance(authors, list):
            return []

        cleaned_authors: list[str] = []
        seen = set()
        for author in authors:
            cleaned = self._clean_person_name(author)
            if not self._is_person_name(cleaned):
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned_authors.append(cleaned)
            if len(cleaned_authors) >= 12:
                break
        return cleaned_authors

    def _normalize_year(self, value: object) -> str:
        """把年份规范成四位数字字符串。"""
        if value is None:
            return ""
        match = _YEAR_PATTERN.search(str(value))
        if not match:
            return ""
        year = match.group(1)
        return year if self._is_valid_year(year) else ""

    def _normalize_doi(self, value: object) -> str:
        """把 DOI 文本规范成标准 DOI。"""
        if value is None:
            return ""
        text = str(value).strip()
        if "doi.org/" in text.lower():
            text = text.split("doi.org/", 1)[1]
        match = _DOI_PATTERN.search(text)
        return match.group(0).rstrip(".,);]") if match else ""

    def _normalize_url(self, value: object) -> str:
        """把 URL 文本规范成标准链接。"""
        if value is None:
            return ""
        text = str(value).strip()
        match = _URL_PATTERN.search(text)
        return match.group(0).rstrip(".,);]") if match else ""

    def _normalize_date(self, value: object) -> str:
        """把出版日期规范为 YYYY-MM-DD、YYYY-MM 或 YYYY，无法识别时返回空字符串。"""
        text = self._clean_text(value)
        if not text:
            return ""
        match = re.search(r"\b(19\d{2}|20\d{2})(?:[-/.年](\d{1,2})(?:[-/.月](\d{1,2}))?)?", text)
        if not match:
            return ""
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        if month and day:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        if month:
            return f"{year}-{int(month):02d}"
        return year

    def _normalize_pages(self, value: object) -> str:
        """清洗页码字段，统一常见连接符并移除首尾多余标点。"""
        text = self._clean_text(value)
        if not text:
            return ""
        return text.replace("--", "-").replace("–", "-").replace("—", "-").strip(" :.,;，；")

    def _normalize_document_type(self, value: object) -> str:
        """把模型返回的文献类型规范为 GB/T 常见类型标识。"""
        text = self._clean_text(value).lower().strip("[]")
        if not text:
            return ""
        type_aliases = {
            "journal": "J",
            "journal article": "J",
            "journal-article": "J",
            "article": "J",
            "期刊": "J",
            "期刊论文": "J",
            "j": "J",
            "j/ol": "J/OL",
            "online journal": "J/OL",
            "conference": "C",
            "conference paper": "C",
            "proceedings": "C",
            "会议": "C",
            "会议论文": "C",
            "c": "C",
            "dissertation": "D",
            "thesis": "D",
            "degree thesis": "D",
            "学位论文": "D",
            "博士论文": "D",
            "硕士论文": "D",
            "d": "D",
            "book": "M",
            "monograph": "M",
            "图书": "M",
            "专著": "M",
            "m": "M",
            "report": "R",
            "technical report": "R",
            "报告": "R",
            "r": "R",
            "preprint": "EB/OL",
            "online": "EB/OL",
            "web": "EB/OL",
            "eb/ol": "EB/OL",
            "ebol": "EB/OL",
            "电子资源": "EB/OL",
        }
        return type_aliases.get(text, text.upper())

    def _infer_document_type(self, *, title: str, venue: str, url: str) -> str:
        """根据标题、来源和链接粗略推断文献类型，作为 LLM 漏填时的兜底。"""
        sample = f"{title} {venue} {url}".lower()
        if re.search(r"(学位论文|博士论文|硕士论文|dissertation|thesis)", sample):
            return "D"
        if re.search(r"(conference|proceedings|symposium|workshop|会议|大会|论文集)", sample):
            return "C"
        if re.search(r"(arxiv|preprint|online|web|网页|网络首发|urlid)", sample):
            return "J/OL" if venue else "EB/OL"
        if venue:
            return "J"
        if url:
            return "EB/OL"
        return ""

    def _normalize_extra_metadata(self, value: object) -> dict[str, str]:
        """规范化扩展元数据字典，只保留可序列化的短文本键值。"""
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, str] = {}
        for key, item in value.items():
            key_text = self._clean_text(key)
            value_text = self._clean_text(item)
            if not key_text or not value_text:
                continue
            normalized[key_text[:80]] = value_text[:500]
        return normalized

    def _normalize_language(self, value: object, title: str, abstract: str) -> str:
        """把语言字段规范成 `zh` 或 `en`。"""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"zh", "zh-cn", "chinese"}:
                return "zh"
            if lowered in {"en", "english"}:
                return "en"

        sample = f"{title} {abstract}"
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", sample))
        ascii_words = len(re.findall(r"[A-Za-z]{3,}", sample))
        return "zh" if chinese_chars >= ascii_words else "en"

    def _clean_text(self, value: object) -> str:
        """清理任意文本中的多余空白。"""
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    def _clean_person_name(self, value: object) -> str:
        """清理作者姓名两端的编号和符号。"""
        text = self._clean_text(value)
        text = re.sub(r"^[\d\W_]+|[\d\W_]+$", "", text)
        return text

    def _looks_like_affiliation(self, line: str) -> bool:
        """判断一行文本是否更像作者单位而不是作者姓名。"""
        lowered = line.lower()
        return any(keyword in lowered for keyword in _AFFILIATION_HINTS)

    def _is_person_name(self, text: str) -> bool:
        """判断一个字符串是否像作者姓名。"""
        if not text or len(text) > 80:
            return False
        if self._looks_like_affiliation(text):
            return False
        if "@" in text or "http" in text.lower():
            return False
        if any(char.isdigit() for char in text):
            return False
        return bool(_ENGLISH_NAME_PATTERN.fullmatch(text) or _CHINESE_NAME_PATTERN.fullmatch(text))

    def _first_valid_year(self, candidates: list[str]) -> str:
        """从候选年份列表中返回第一个合理年份。"""
        for year in candidates:
            if self._is_valid_year(year):
                return year
        return ""

    def _is_valid_year(self, value: str) -> bool:
        """判断年份是否落在合理的论文发表区间。"""
        if not value.isdigit():
            return False
        year = int(value)
        return _YEAR_MIN <= year <= _YEAR_MAX

    def _deduplicate_preserve_order(self, values: list[str]) -> list[str]:
        """去重并保留原始顺序。"""
        result: list[str] = []
        seen = set()
        for value in values:
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(value)
        return result

    def _build_default_citation(
        self,
        *,
        authors: list[str],
        title: str,
        year: str,
        venue: str,
        doi: str,
        url: str,
        publication_date: str,
        document_type: str,
        publisher: str,
        publisher_place: str,
        volume: str,
        issue: str,
        pages: str,
        article_number: str,
        degree_institution: str,
        degree_location: str,
        proceedings_title: str,
        conference_name: str,
    ) -> str:
        """生成近似 GB/T 7714-2015 的默认引用字符串。"""
        return format_gbt7714_citation(
            authors=authors,
            title=title,
            year=publication_date or year,
            venue=venue,
            doi=doi,
            url=url,
            source_type="local",
            publication_date=publication_date,
            document_type=document_type,
            publisher=publisher,
            publisher_place=publisher_place,
            volume=volume,
            issue=issue,
            pages=pages,
            article_number=article_number,
            degree_institution=degree_institution,
            degree_location=degree_location,
            proceedings_title=proceedings_title,
            conference_name=conference_name,
        )


class PathFallback:
    """处理文件名回退逻辑的小工具。"""

    @staticmethod
    def name_without_suffix(file_name: str) -> str:
        """去掉扩展名，用作标题兜底值。"""
        if "." not in file_name:
            return file_name
        return file_name.rsplit(".", 1)[0]
