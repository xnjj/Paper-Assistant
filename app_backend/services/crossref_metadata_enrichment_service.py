from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import config_data as config
from app_backend.services.citation_formatter import format_gbt7714_citation


_CROSSREF_WORKS_API = "https://api.crossref.org/works"
_TITLE_MATCH_THRESHOLD = 0.88
_CROSSREF_SELECT_FIELDS = [
    "DOI",
    "title",
    "author",
    "container-title",
    "published",
    "published-print",
    "published-online",
    "issued",
    "is-referenced-by-count",
    "references-count",
    "abstract",
    "URL",
    "type",
    "publisher",
    "volume",
    "issue",
    "page",
    "article-number",
]


@dataclass
class CrossrefMetadata:
    """保存从 Crossref 获取到的正式出版元数据。"""

    doi: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    publication_date: str = ""
    venue: str = ""
    publisher: str = ""
    document_type: str = ""
    crossref_type: str = ""
    url: str = ""
    abstract: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    article_number: str = ""
    references_count: int | None = None
    is_referenced_by_count: int | None = None
    match_score: float = 1.0


class CrossrefMetadataEnrichmentService:
    """使用 Crossref 为外部候选或最终引用到的本地文献补全正式出版元数据。"""

    def __init__(self, *, timeout_seconds: int = 15) -> None:
        """初始化 Crossref 补全服务，并创建进程内简单缓存。"""
        self.timeout_seconds = timeout_seconds
        self._doi_cache: dict[str, CrossrefMetadata | None] = {}
        self._title_cache: dict[str, CrossrefMetadata | None] = {}

    def enrich_documents(
        self,
        documents: list[dict[str, Any]],
        *,
        include_local: bool = False,
    ) -> list[dict[str, Any]]:
        """批量补全文献字典；默认仅补外部文献，include_local=True 时也补最终引用到的本地文献。"""
        enriched_documents = list(documents)
        enrichment_tasks: list[tuple[int, dict[str, Any]]] = []
        for index, document in enumerate(documents):
            if index >= config.DEFAULT_EXTERNAL_FINAL_LIMIT:
                continue
            if not self._should_enrich(document, include_local=include_local):
                continue
            enrichment_tasks.append((index, document))

        if not enrichment_tasks:
            return enriched_documents

        max_workers = max(1, min(config.MAX_PARALLEL_CROSSREF_QUERIES, len(enrichment_tasks)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self.enrich_document, document): index
                for index, document in enrichment_tasks
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    enriched_documents[index] = future.result()
                except Exception as exc:  # pragma: no cover - 外部服务异常不应中断主回答链路
                    print(f"Crossref metadata enrichment task failed: {exc}")
        return enriched_documents

    def enrich_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """补全单篇文献；失败时返回原始文献，保证主问答链路不中断。"""
        try:
            metadata = self._lookup_crossref_metadata(document)
        except Exception as exc:  # pragma: no cover - 外部服务失败时以不中断主链路为主
            print(f"Crossref metadata enrichment failed: {exc}")
            metadata = None
        if metadata is None:
            return document
        return self._merge_document_metadata(document, metadata)

    def _should_enrich(self, document: dict[str, Any], *, include_local: bool = False) -> bool:
        """判断当前文献是否适合使用 Crossref 补全，可按需允许本地文献参与。"""
        source_type = str(document.get("source_type") or "").lower()
        source_id = str(document.get("source_id") or "").lower()
        is_external = source_type == "external" or source_id.startswith("ext_")
        is_local = include_local and (
            source_type in {"local", "local_folder"} or source_id.startswith("doc_")
        )
        if not is_external and not is_local:
            return False
        return bool(str(document.get("doi") or "").strip() or str(document.get("title") or "").strip())

    def _lookup_crossref_metadata(self, document: dict[str, Any]) -> CrossrefMetadata | None:
        """优先按 DOI 精确查询，缺 DOI 时再按标题检索。"""
        doi = self._normalize_doi(document.get("doi"))
        if doi:
            return self._lookup_by_doi(doi)

        title = str(document.get("title") or "").strip()
        if not title:
            return None
        return self._lookup_by_title(title)

    def _lookup_by_doi(self, doi: str) -> CrossrefMetadata | None:
        """按 DOI 从 Crossref 获取元数据。"""
        cache_key = doi.lower()
        if cache_key in self._doi_cache:
            return self._doi_cache[cache_key]

        url = f"{_CROSSREF_WORKS_API}/{urllib.parse.quote(doi, safe='')}"
        payload = self._fetch_json(url)
        message = payload.get("message")
        metadata = self._work_to_metadata(message) if isinstance(message, dict) else None
        self._doi_cache[cache_key] = metadata
        return metadata

    def _lookup_by_title(self, title: str) -> CrossrefMetadata | None:
        """按标题检索 Crossref，并用标题相似度筛掉明显误配结果。"""
        cache_key = self._normalize_for_match(title)
        if cache_key in self._title_cache:
            return self._title_cache[cache_key]

        params = {
            "query.title": title,
            "rows": "3",
            "sort": "score",
            "order": "desc",
            "select": ",".join(_CROSSREF_SELECT_FIELDS),
        }
        mailto = os.getenv("CROSSREF_MAILTO", "").strip()
        if mailto:
            params["mailto"] = mailto
        url = f"{_CROSSREF_WORKS_API}?{urllib.parse.urlencode(params)}"
        payload = self._fetch_json(url)
        message = payload.get("message")
        items = message.get("items", []) if isinstance(message, dict) else []

        best_metadata: CrossrefMetadata | None = None
        best_score = 0.0
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            metadata = self._work_to_metadata(item)
            if metadata is None:
                continue
            score = self._title_similarity(title, metadata.title)
            if score > best_score:
                metadata.match_score = score
                best_metadata = metadata
                best_score = score

        if best_score < _TITLE_MATCH_THRESHOLD:
            best_metadata = None
        self._title_cache[cache_key] = best_metadata
        return best_metadata

    def _fetch_json(self, url: str) -> dict[str, Any]:
        """请求 Crossref REST API 并解析 JSON。"""
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": self._build_user_agent(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in {404, 429, 500, 502, 503, 504}:
                return {}
            raise

    def _build_user_agent(self) -> str:
        """构造 Crossref 推荐的可联系 User-Agent。"""
        mailto = os.getenv("CROSSREF_MAILTO", "").strip()
        if mailto:
            return f"RAG-Paper-Assistant/0.1 (mailto:{mailto})"
        return "RAG-Paper-Assistant/0.1"

    def _work_to_metadata(self, work: dict[str, Any] | None) -> CrossrefMetadata | None:
        """把 Crossref work 对象转换为项目内部元数据结构。"""
        if not isinstance(work, dict):
            return None
        doi = self._normalize_doi(work.get("DOI"))
        title = self._first_text(work.get("title"))
        if not doi and not title:
            return None

        publication_date = self._extract_publication_date(work)
        crossref_type = str(work.get("type") or "").strip()
        return CrossrefMetadata(
            doi=doi,
            title=title,
            authors=self._extract_authors(work),
            year=publication_date[:4] if publication_date else self._extract_year(work),
            publication_date=publication_date,
            venue=self._first_text(work.get("container-title")),
            publisher=str(work.get("publisher") or "").strip(),
            document_type=self._map_crossref_type_to_gbt(crossref_type),
            crossref_type=crossref_type,
            url=str(work.get("URL") or (f"https://doi.org/{doi}" if doi else "")).strip(),
            abstract=self._clean_crossref_abstract(str(work.get("abstract") or "")),
            volume=str(work.get("volume") or "").strip(),
            issue=str(work.get("issue") or "").strip(),
            pages=str(work.get("page") or "").strip(),
            article_number=str(work.get("article-number") or "").strip(),
            references_count=self._coerce_int(work.get("references-count")),
            is_referenced_by_count=self._coerce_int(work.get("is-referenced-by-count")),
        )

    def _merge_document_metadata(self, document: dict[str, Any], metadata: CrossrefMetadata) -> dict[str, Any]:
        """按字段可信度把 Crossref 正式出版元数据合并回外部候选文献。"""
        merged = dict(document)
        original_url = str(merged.get("url") or "").strip()
        if original_url and not merged.get("source_url"):
            merged["source_url"] = original_url

        merged["doi"] = metadata.doi or str(merged.get("doi") or "")
        merged["title"] = str(merged.get("title") or metadata.title or "")
        merged["authors"] = merged.get("authors") or metadata.authors
        merged["year"] = metadata.year or str(merged.get("year") or "")
        merged["publication_date"] = metadata.publication_date or str(merged.get("publication_date") or "")
        merged["venue"] = metadata.venue or str(merged.get("venue") or "")
        merged["publisher"] = metadata.publisher or str(merged.get("publisher") or "")
        merged["volume"] = metadata.volume or str(merged.get("volume") or "")
        merged["issue"] = metadata.issue or str(merged.get("issue") or "")
        merged["pages"] = metadata.pages or str(merged.get("pages") or "")
        merged["article_number"] = metadata.article_number or str(merged.get("article_number") or "")
        merged["document_type"] = metadata.document_type or str(merged.get("document_type") or "")
        merged["crossref_type"] = metadata.crossref_type
        merged["crossref_matched"] = True
        merged["crossref_match_score"] = metadata.match_score
        merged["references_count"] = metadata.references_count
        merged["is_referenced_by_count"] = metadata.is_referenced_by_count
        if metadata.url:
            merged["url"] = metadata.url
        if not merged.get("abstract") and metadata.abstract:
            merged["abstract"] = metadata.abstract

        metadata_sources = merged.get("metadata_sources")
        if not isinstance(metadata_sources, list):
            metadata_sources = []
        if "crossref" not in metadata_sources:
            metadata_sources = [*metadata_sources, "crossref"]
        merged["metadata_sources"] = metadata_sources
        merged["citation_text_default"] = format_gbt7714_citation(
            authors=merged.get("authors") or [],
            title=str(merged.get("title") or ""),
            year=str(merged.get("year") or ""),
            venue=str(merged.get("venue") or ""),
            doi=str(merged.get("doi") or ""),
            url=str(merged.get("url") or ""),
            source_type=str(merged.get("source_type") or "external"),
            document_type=str(merged.get("document_type") or ""),
            publisher=str(merged.get("publisher") or ""),
            publisher_place=str(merged.get("publisher_place") or ""),
            volume=str(merged.get("volume") or ""),
            issue=str(merged.get("issue") or ""),
            pages=str(merged.get("pages") or ""),
            publication_date=str(merged.get("publication_date") or ""),
            article_number=str(merged.get("article_number") or ""),
            degree_institution=str(merged.get("degree_institution") or ""),
            degree_location=str(merged.get("degree_location") or ""),
            proceedings_title=str(merged.get("proceedings_title") or ""),
            conference_name=str(merged.get("conference_name") or ""),
        )
        return merged

    def _extract_authors(self, work: dict[str, Any]) -> list[str]:
        """从 Crossref author 字段提取作者姓名列表。"""
        authors_payload = work.get("author")
        if not isinstance(authors_payload, list):
            return []

        authors: list[str] = []
        for author in authors_payload:
            if not isinstance(author, dict):
                continue
            given = str(author.get("given") or "").strip()
            family = str(author.get("family") or "").strip()
            name = " ".join(part for part in [given, family] if part).strip()
            if not name:
                name = str(author.get("name") or "").strip()
            if name:
                authors.append(name)
        return authors

    def _extract_publication_date(self, work: dict[str, Any]) -> str:
        """按优先级从 Crossref 日期字段中提取出版日期。"""
        for field_name in ("published-online", "published-print", "published", "issued"):
            parsed = self._parse_crossref_date(work.get(field_name))
            if parsed:
                return parsed
        return ""

    def _extract_year(self, work: dict[str, Any]) -> str:
        """从 Crossref 日期字段中兜底提取年份。"""
        publication_date = self._extract_publication_date(work)
        return publication_date[:4] if publication_date else ""

    def _parse_crossref_date(self, value: Any) -> str:
        """解析 Crossref date-parts 字段为 YYYY-MM-DD / YYYY-MM / YYYY。"""
        if not isinstance(value, dict):
            return ""
        date_parts = value.get("date-parts")
        if not isinstance(date_parts, list) or not date_parts:
            return ""
        first_part = date_parts[0]
        if not isinstance(first_part, list) or not first_part:
            return ""
        try:
            parts = [int(item) for item in first_part if str(item).strip()]
        except (TypeError, ValueError):
            return ""
        if len(parts) >= 3:
            return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
        if len(parts) == 2:
            return f"{parts[0]:04d}-{parts[1]:02d}"
        return f"{parts[0]:04d}" if parts else ""

    def _map_crossref_type_to_gbt(self, crossref_type: str) -> str:
        """把 Crossref type 映射为 GB/T 7714-2015 文献类型标识。"""
        normalized = (crossref_type or "").strip().lower()
        
        type_mapping = {
            # 期刊 (J)
            "journal-article": "J",
            "journal": "J",
            "journal-volume": "J",
            "journal-issue": "J",
            
            # 会议录 (C)
            "proceedings-article": "C",
            "proceedings": "C",
            "proceedings-series": "C",
            
            # 专著/图书 (M)
            "book": "M",
            "book-chapter": "M",
            "book-section": "M",
            "book-part": "M",
            "book-series": "M",
            "book-set": "M",
            "book-track": "M",
            "monograph": "M",
            "reference-book": "M",
            "edited-book": "M",
            
            # 学位论文 (D)
            "dissertation": "D",
            
            # 报告 (R)
            "report": "R",
            "report-series": "R",
            
            # 标准 (S)
            "standard": "S",
            "standard-series": "S",
            
            # 数据库/数据集 (DB)
            "dataset": "DB",
            
            # 电子公告/预印本 (EB/OL)
            "posted-content": "EB/OL",
            "preprint": "EB/OL",
            
            # 其他/组件/基金等 (Z)
            "component": "Z",
            "peer-review": "Z",
            "grant": "Z",
            "award": "Z",
            "other": "Z",
        }
        
        return type_mapping.get(normalized, "Z")

    def _clean_crossref_abstract(self, value: str) -> str:
        """清理 Crossref abstract 中常见的 JATS/HTML 标签。"""
        if not value:
            return ""
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()

    def _title_similarity(self, left: str, right: str) -> float:
        """计算标题归一化后的相似度，用于标题检索结果校验。"""
        left_key = self._normalize_for_match(left)
        right_key = self._normalize_for_match(right)
        if not left_key or not right_key:
            return 0.0
        if left_key == right_key:
            return 1.0
        return SequenceMatcher(None, left_key, right_key).ratio()

    def _normalize_for_match(self, value: str) -> str:
        """把标题或 DOI 规整为适合匹配比较的文本。"""
        normalized = re.sub(r"https?://doi\.org/", "", str(value or "").strip().lower())
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _normalize_doi(self, value: Any) -> str:
        """规范化 DOI 字段，去掉 URL 前缀和多余标点。"""
        doi = str(value or "").strip()
        if not doi:
            return ""
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        return doi.strip().rstrip(".,;")

    def _first_text(self, value: Any) -> str:
        """从 Crossref 常见数组文本字段中取第一项。"""
        if isinstance(value, list) and value:
            return str(value[0] or "").strip()
        return str(value or "").strip()

    def _coerce_int(self, value: Any) -> int | None:
        """把 Crossref 数值字段安全转换为整数。"""
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
