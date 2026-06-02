from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from paper_source_mcp_server.providers.base import ExternalPaperProvider
from paper_source_mcp_server.schemas import ExternalFulltextRecord, ExternalPaperRecord


class OpenAlexProvider(ExternalPaperProvider):
    """基于 OpenAlex Works API 的论文来源 provider。"""

    source_name = "openalex"
    api_base_url = "https://api.openalex.org/works"

    def search(
        self,
        query: list[str],
        *,
        limit: int = 10,
        date_from: str | None = None,
        sortby: str = "relevance",
        orderby: str = "descending",
    ) -> list[ExternalPaperRecord]:
        """调用 OpenAlex Works API 搜索论文候选。"""
        normalized_query = self._build_search_text(query)
        if not normalized_query:
            return []

        request_url = self._build_search_url(
            normalized_query,
            limit=max(1, limit),
            date_from=date_from,
            sortby="relevance",
            orderby="descending",
        )
        payload = self._fetch_json(request_url)
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            return []

        records = [
            record
            for record in (self._work_to_record(item) for item in raw_results)
            if record is not None
        ]
        return self._filter_records_by_date(records, date_from=date_from)[:limit]

    def get_detail(self, external_id: str) -> ExternalPaperRecord | None:
        """按 OpenAlex work ID 获取单篇论文详情。"""
        normalized_id = external_id.strip()
        if not normalized_id:
            return None

        if not normalized_id.startswith("https://openalex.org/"):
            normalized_id = f"https://openalex.org/{normalized_id}"
        request_url = f"{self.api_base_url}/{urllib.parse.quote(normalized_id.rsplit('/', 1)[-1])}"
        payload = self._fetch_json(request_url)
        return self._work_to_record(payload)

    def resolve_fulltext(self, record: ExternalPaperRecord) -> ExternalFulltextRecord | None:
        """解析 OpenAlex 记录中已有的开放 PDF 或落地页信息。"""
        if not record.external_id.strip():
            return None
        landing_page_url = record.url or f"https://openalex.org/{record.external_id}"
        return ExternalFulltextRecord(
            source=self.source_name,
            external_id=record.external_id,
            title=record.title,
            pdf_url=record.pdf_url,
            download_url=record.pdf_url,
            landing_page_url=landing_page_url,
            content_type="application/pdf" if record.pdf_url else "",
            license="",
            is_open_access=bool(record.pdf_url),
        )

    def _build_search_url(
        self,
        query: str,
        *,
        limit: int,
        date_from: str | None,
        sortby: str,
        orderby: str,
    ) -> str:
        """构造 OpenAlex Works 搜索 URL。"""
        params: dict[str, str] = {
            "search": query,
            "per-page": str(max(1, min(limit, 200))),
            "page": "1",
            "sort": self._map_sort(sortby, orderby),
        }
        normalized_date = self._format_openalex_date(date_from)
        if normalized_date:
            params["filter"] = f"from_publication_date:{normalized_date}"

        mailto = os.getenv("OPENALEX_MAILTO", "").strip()
        if mailto:
            params["mailto"] = mailto
        return f"{self.api_base_url}?{urllib.parse.urlencode(params)}"

    def _map_sort(self, sortby: str, orderby: str) -> str:
        """把统一排序字段映射为 OpenAlex 支持的排序表达式。"""
        normalized_sort = (sortby or "relevance").strip()
        normalized_order = (orderby or "descending").strip()
        direction = "asc" if normalized_order == "ascending" else "desc"
        if normalized_sort in {"submittedDate", "publication_date", "publicationDate"}:
            return f"publication_date:{direction}"
        return f"relevance_score:{direction}"

    def _build_search_text(self, query: list[str]) -> str:
        """把统一关键词列表转换为 OpenAlex search 文本。"""
        keywords: list[str] = []
        for item in query:
            keyword = " ".join(str(item).split())
            if keyword and keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 4:
                break
        return " ".join(keywords)

    def _format_openalex_date(self, value: str | None) -> str:
        """把 yyyymmdd 日期转换为 OpenAlex 接受的 YYYY-MM-DD。"""
        normalized = (value or "").strip()
        if not normalized:
            return ""
        try:
            parsed = datetime.strptime(normalized, "%Y%m%d")
        except ValueError:
            return ""
        return parsed.date().isoformat()

    def _fetch_json(self, request_url: str) -> dict[str, Any]:
        """请求 OpenAlex API 并解析 JSON 响应。"""
        request = urllib.request.Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "paper-source-mcp-server/0.1 (OpenAlex provider)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise
        except Exception as exc:
            raise RuntimeError(f"OpenAlex API 请求失败：{exc}") from exc

    def _work_to_record(self, payload: Any) -> ExternalPaperRecord | None:
        """把 OpenAlex work 结构转换为统一论文记录。"""
        if not isinstance(payload, dict):
            return None

        openalex_id = str(payload.get("id") or "").strip()
        external_id = openalex_id.rsplit("/", 1)[-1]
        title = str(payload.get("title") or payload.get("display_name") or "").strip()
        if not external_id or not title:
            return None

        primary_location = payload.get("primary_location")
        if not isinstance(primary_location, dict):
            primary_location = {}
        source = primary_location.get("source")
        if not isinstance(source, dict):
            source = {}

        return ExternalPaperRecord(
            source=self.source_name,
            external_id=external_id,
            title=self._normalize_text(title),
            authors=self._extract_authors(payload),
            year=str(payload.get("publication_year") or ""),
            venue=str(source.get("display_name") or ""),
            doi=self._normalize_doi(str(payload.get("doi") or "")),
            url=str(primary_location.get("landing_page_url") or openalex_id),
            abstract=self._restore_abstract(payload.get("abstract_inverted_index")),
            pdf_url=str(primary_location.get("pdf_url") or ""),
            relevance_score=self._coerce_score(payload.get("relevance_score")),
            published_at=str(payload.get("publication_date") or ""),
        )

    def _extract_authors(self, payload: dict[str, Any]) -> list[str]:
        """从 OpenAlex authorships 字段提取作者列表。"""
        authorships = payload.get("authorships")
        if not isinstance(authorships, list):
            return []

        authors: list[str] = []
        for authorship in authorships:
            if not isinstance(authorship, dict):
                continue
            author = authorship.get("author")
            if not isinstance(author, dict):
                continue
            name = str(author.get("display_name") or "").strip()
            if name:
                authors.append(name)
        return authors

    def _restore_abstract(self, inverted_index: Any) -> str:
        """把 OpenAlex 的倒排摘要还原为普通文本。"""
        if not isinstance(inverted_index, dict):
            return ""

        positioned_words: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            if not isinstance(positions, list):
                continue
            for position in positions:
                try:
                    positioned_words.append((int(position), str(word)))
                except (TypeError, ValueError):
                    continue

        if not positioned_words:
            return ""
        positioned_words.sort(key=lambda item: item[0])
        return " ".join(word for _, word in positioned_words)

    def _filter_records_by_date(
        self,
        records: list[ExternalPaperRecord],
        *,
        date_from: str | None,
    ) -> list[ExternalPaperRecord]:
        """本地兜底按日期过滤，防止接口返回超出范围的数据。"""
        normalized_date = self._format_openalex_date(date_from)
        if not normalized_date:
            return records
        filtered_records: list[ExternalPaperRecord] = []
        for record in records:
            if not record.published_at:
                continue
            if record.published_at >= normalized_date:
                filtered_records.append(record)
        return filtered_records

    def _normalize_doi(self, value: str) -> str:
        """清理 OpenAlex DOI 字段中的 URL 前缀。"""
        normalized = value.strip()
        return normalized.removeprefix("https://doi.org/").removeprefix("http://doi.org/")

    def _normalize_text(self, value: str) -> str:
        """清理文本中的多余空白。"""
        return " ".join(value.split())

    def _coerce_score(self, value: Any) -> float | None:
        """把 OpenAlex 相关性分数安全转换为浮点数。"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
