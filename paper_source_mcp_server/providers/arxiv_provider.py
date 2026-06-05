from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import socket
import threading
from datetime import datetime

from paper_source_mcp_server.providers.base import ExternalPaperProvider
from paper_source_mcp_server.schemas import ExternalFulltextRecord, ExternalPaperRecord


class ArxivProvider(ExternalPaperProvider):
    """基于 arXiv 官方 API 的论文来源 provider。"""

    source_name = "arxiv"
    api_base_url = "http://export.arxiv.org/api/query"
    _request_lock = threading.Lock()
    _last_request_at = 0.0
    _min_request_interval_seconds = 3.5

    def search(
        self,
        query: list[str],
        *,
        limit: int = 10,
        date_from: str | None = None,
        sortby: str = "relevance",
        orderby: str = "descending",
    ) -> list[ExternalPaperRecord]:
        """调用 arXiv 官方 API 搜索论文候选，并在本地补做日期过滤。"""
        search_query = self._build_search_query(query)
        request_limit = self._resolve_request_limit(limit=limit, date_from=date_from)
        request_url = self._build_query_url(
            search_query=search_query,
            start=0,
            max_results=request_limit,
            sort_by="submittedDate",
            sort_order="descending",
        )
        root = self._fetch_feed(request_url)
        entries = root.findall(self._atom_tag("entry"))
        records = [
            record
            for record in (self._entry_to_record(entry) for entry in entries)
            if record is not None
        ]
        filtered_records = self._filter_records_by_date(records, date_from=date_from)
        return filtered_records[:limit]

    def get_detail(self, external_id: str) -> ExternalPaperRecord | None:
        """按 arXiv 编号获取单篇论文详情。"""
        if not external_id.strip():
            return None
        request_url = self._build_query_url(f"id:{external_id}", start=0, max_results=1)
        root = self._fetch_feed(request_url)
        entry = root.find(self._atom_tag("entry"))
        if entry is None:
            return None
        return self._entry_to_record(entry)

    def resolve_fulltext(self, record: ExternalPaperRecord) -> ExternalFulltextRecord | None:
        """解析 arXiv 论文的 PDF 与落地页链接。"""
        if not record.external_id.strip():
            return None

        pdf_url = record.pdf_url or f"https://arxiv.org/pdf/{record.external_id}.pdf"
        landing_page_url = record.url or f"https://arxiv.org/abs/{record.external_id}"
        return ExternalFulltextRecord(
            source=self.source_name,
            external_id=record.external_id,
            title=record.title,
            pdf_url=pdf_url,
            download_url=pdf_url,
            landing_page_url=landing_page_url,
            content_type="application/pdf",
            license="",
            is_open_access=True,
        )

    def _build_search_query(self, query: list[str]) -> str:
        """把统一关键词列表转换为 arXiv 使用的 all:\"...\" AND 表达式。"""
        keywords = self._normalize_keywords(query)
        if not keywords:
            return "all:*"
        return " AND ".join(f'all:"{keyword}"' for keyword in keywords)

    def _resolve_request_limit(self, *, limit: int, date_from: str | None) -> int:
        """根据是否需要日期过滤，决定向 arXiv 额外多取多少结果。"""
        if date_from is None:
            return limit
        return min(limit, 20)

    def _filter_records_by_date(
        self,
        records: list[ExternalPaperRecord],
        *,
        date_from: str | None,
    ) -> list[ExternalPaperRecord]:
        """按 yyyymmdd 日期下限过滤结果，避免把日期范围交给 arXiv 查询。"""
        if date_from is None:
            return records

        threshold = self._parse_date_from(date_from)
        if threshold is None:
            return records

        filtered_records: list[ExternalPaperRecord] = []
        for record in records:
            published_at = getattr(record, "published_at", "")
            record_date = self._parse_record_date(str(published_at or ""))
            if record_date is None:
                continue
            if record_date >= threshold:
                filtered_records.append(record)
        return filtered_records

    def _normalize_keywords(self, query: list[str]) -> list[str]:
        """清理统一关键词列表，最多保留 4 个关键词或短语。"""
        keywords: list[str] = []
        for item in query:
            keyword = " ".join(str(item).replace('"', " ").split())
            if keyword and keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 4:
                break
        return keywords

    def _parse_date_from(self, value: str) -> datetime | None:
        """把 yyyymmdd 日期下限解析为 datetime。"""
        normalized = (value or "").strip()
        if not normalized:
            return None
        try:
            return datetime.strptime(normalized, "%Y%m%d")
        except ValueError:
            return None

    def _parse_record_date(self, value: str) -> datetime | None:
        """解析 arXiv published 字段中的日期部分。"""
        normalized = (value or "").strip()
        if not normalized:
            return None
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            try:
                return datetime.strptime(normalized[:10], "%Y-%m-%d")
            except ValueError:
                return None

    def _build_query_url(
        self,
        search_query: str,
        *,
        start: int,
        max_results: int,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> str:
        """根据查询表达式构造 arXiv API 请求地址。"""
        params = {
            "search_query": search_query,
            "start": str(start),
            "max_results": str(max_results),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        return f"{self.api_base_url}?{urllib.parse.urlencode(params)}"

    def _fetch_feed(self, request_url: str) -> ET.Element:
        """请求 arXiv API；每个 query 只请求一次，不做内部重试。"""
        request = urllib.request.Request(
            request_url,
            headers={
                "User-Agent": "paper-source-mcp-server/0.1 (RAG-Agent external search test)",
            },
        )

        try:
            self._wait_for_rate_limit_window()
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
            return ET.fromstring(payload)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"arXiv API 请求失败：HTTP Error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"arXiv API 请求失败：{exc}") from exc
        except (TimeoutError, socket.timeout, OSError) as exc:
            raise RuntimeError(f"arXiv API 请求失败：{exc}") from exc

    def _wait_for_rate_limit_window(self) -> None:
        """在本进程内做基础请求间隔控制，降低触发 429 的概率。"""
        with self._request_lock:
            now = time.time()
            elapsed = now - self._last_request_at
            wait_seconds = self._min_request_interval_seconds - elapsed
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._last_request_at = time.time()

    def _entry_to_record(self, entry: ET.Element) -> ExternalPaperRecord | None:
        """把单个 Atom entry 转换为统一论文记录。"""
        title = self._read_text(entry, self._atom_tag("title"))
        entry_id = self._read_text(entry, self._atom_tag("id"))
        summary = self._read_text(entry, self._atom_tag("summary"))
        published = self._read_text(entry, self._atom_tag("published"))
        external_id = self._extract_arxiv_id(entry_id)
        if not title or not external_id:
            return None

        authors = [
            self._read_text(author, self._atom_tag("name"))
            for author in entry.findall(self._atom_tag("author"))
        ]
        authors = [item for item in authors if item]

        pdf_url = ""
        for link in entry.findall(self._atom_tag("link")):
            link_type = (link.attrib.get("type") or "").strip().lower()
            title_attr = (link.attrib.get("title") or "").strip().lower()
            href = (link.attrib.get("href") or "").strip()
            if link_type == "application/pdf" or title_attr == "pdf":
                pdf_url = href
                break

        return ExternalPaperRecord(
            source=self.source_name,
            external_id=external_id,
            title=self._normalize_text(title),
            authors=authors,
            year=published[:4] if len(published) >= 4 else "",
            venue="arXiv",
            doi="",
            url=entry_id.replace("http://", "https://"),
            abstract=self._normalize_text(summary),
            pdf_url=pdf_url.replace("http://", "https://"),
            relevance_score=None,
            published_at=published,
        )

    def _read_text(self, element: ET.Element, tag: str) -> str:
        """读取指定 XML 子节点的文本内容。"""
        child = element.find(tag)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """从 arXiv entry id 中提取 arXiv 编号。"""
        normalized_id = entry_id.strip().rstrip("/")
        if not normalized_id:
            return ""
        return normalized_id.rsplit("/", maxsplit=1)[-1]

    def _normalize_text(self, value: str) -> str:
        """清理 Atom 文本中的多余空白。"""
        return " ".join(value.split())

    def _atom_tag(self, name: str) -> str:
        """构造 Atom XML 命名空间下的标签名。"""
        return f"{{http://www.w3.org/2005/Atom}}{name}"
