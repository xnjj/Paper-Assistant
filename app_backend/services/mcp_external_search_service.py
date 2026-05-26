from __future__ import annotations

from typing import Any, Protocol

from app_backend.services.external_search_service import (
    ExternalFulltextPayload,
    ExternalPaperCandidate,
    ExternalSearchService,
)


class MCPToolInvoker(Protocol):
    """定义 MCP 工具调用器需要提供的最小接口。"""

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用指定 MCP 工具，并返回结构化结果。"""
        ...


class MCPExternalSearchService(ExternalSearchService):
    """把外部论文 MCP 工具适配为项目内部的外部检索服务。"""

    def __init__(
        self,
        tool_invoker: MCPToolInvoker | None = None,
        *,
        search_tool_name: str = "search_external_papers",
        detail_tool_name: str = "get_external_paper_detail",
        fulltext_tool_name: str = "resolve_external_fulltext",
        default_source: str = "arxiv",
    ) -> None:
        """初始化 MCP 外部检索适配器。"""
        self.tool_invoker = tool_invoker
        self.search_tool_name = search_tool_name
        self.detail_tool_name = detail_tool_name
        self.fulltext_tool_name = fulltext_tool_name
        self.default_source = default_source

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 10,
        year_from: int | None = None,
    ) -> list[ExternalPaperCandidate]:
        """调用 MCP 检索工具获取外部论文候选。"""
        if self.tool_invoker is None:
            return []

        try:
            raw_result = self.tool_invoker.call_tool(
                self.search_tool_name,
                {
                    "query": query,
                    "limit": limit,
                    "year_from": year_from,
                    "sort_by": "submittedDate" if year_from is not None else "relevance",
                    "sort_order": "descending",
                    "sources": [self.default_source],
                },
            )
        except Exception as exc:
            print(f"MCP external search failed: {exc}")
            return []

        return self._coerce_candidate_list(raw_result)

    def get_paper_detail(self, external_id: str) -> ExternalPaperCandidate | None:
        """调用 MCP 详情工具获取单篇外部论文信息。"""
        if self.tool_invoker is None:
            return None

        try:
            raw_result = self.tool_invoker.call_tool(
                self.detail_tool_name,
                {"source": self.default_source, "external_id": external_id},
            )
        except Exception as exc:
            print(f"MCP external detail lookup failed: {exc}")
            return None

        return self._coerce_candidate(raw_result)

    def resolve_fulltext(self, candidate: ExternalPaperCandidate) -> ExternalFulltextPayload | None:
        """调用 MCP 全文解析工具获取 PDF 或落地页信息。"""
        if self.tool_invoker is None:
            return None

        try:
            raw_result = self.tool_invoker.call_tool(
                self.fulltext_tool_name,
                {
                    "source": candidate.source or self.default_source,
                    "external_id": candidate.external_id,
                    "title": candidate.title,
                    "doi": candidate.doi,
                    "url": candidate.url,
                    "pdf_url": candidate.pdf_url,
                },
            )
        except Exception as exc:
            print(f"MCP external fulltext resolution failed: {exc}")
            return None

        return self._coerce_fulltext_payload(raw_result, candidate)

    def _coerce_candidate_list(self, payload: Any) -> list[ExternalPaperCandidate]:
        """把 MCP 返回的原始列表结果规整为外部论文候选列表。"""
        if isinstance(payload, dict):
            items = payload.get("results")
        else:
            items = payload

        if not isinstance(items, list):
            return []

        candidates: list[ExternalPaperCandidate] = []
        for item in items:
            candidate = self._coerce_candidate(item)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _coerce_candidate(self, payload: Any) -> ExternalPaperCandidate | None:
        """把 MCP 返回的单篇论文结构规整为项目内部候选对象。"""
        if not isinstance(payload, dict):
            return None

        title = str(payload.get("title") or "").strip()
        external_id = str(payload.get("external_id") or payload.get("id") or "").strip()
        if not title or not external_id:
            return None

        authors = self._coerce_authors(payload.get("authors"))
        doi = str(payload.get("doi") or "").strip()
        venue = str(payload.get("venue") or payload.get("journal") or "").strip()
        year = str(payload.get("year") or "").strip()
        url = str(payload.get("url") or payload.get("landing_page_url") or "").strip()
        abstract = str(payload.get("abstract") or "").strip()
        pdf_url = str(payload.get("pdf_url") or "").strip() or None
        source = str(payload.get("source") or self.default_source).strip() or self.default_source
        relevance_score = self._coerce_score(payload.get("relevance_score"))

        return ExternalPaperCandidate(
            source=source,
            external_id=external_id,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            abstract=abstract,
            citation_text_default=self._build_citation_text(
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                doi=doi,
            ),
            pdf_url=pdf_url,
            relevance_score=relevance_score,
        )

    def _coerce_fulltext_payload(
        self,
        payload: Any,
        candidate: ExternalPaperCandidate,
    ) -> ExternalFulltextPayload | None:
        """把 MCP 返回的全文信息规整为项目内部全文对象。"""
        if not isinstance(payload, dict):
            return None

        return ExternalFulltextPayload(
            source=str(payload.get("source") or candidate.source),
            external_id=str(payload.get("external_id") or candidate.external_id),
            title=str(payload.get("title") or candidate.title),
            pdf_url=str(payload.get("pdf_url") or candidate.pdf_url or ""),
            download_url=str(payload.get("download_url") or ""),
            landing_page_url=str(payload.get("landing_page_url") or candidate.url or ""),
            content_type=str(payload.get("content_type") or ""),
            license=str(payload.get("license") or ""),
            is_open_access=bool(payload.get("is_open_access", False)),
        )

    def _coerce_authors(self, payload: Any) -> list[str]:
        """把不同格式的作者字段统一转换为字符串列表。"""
        if isinstance(payload, list):
            authors: list[str] = []
            for item in payload:
                if isinstance(item, str):
                    value = item.strip()
                    if value:
                        authors.append(value)
                elif isinstance(item, dict):
                    value = str(item.get("name") or item.get("full_name") or "").strip()
                    if value:
                        authors.append(value)
            return authors
        if isinstance(payload, str):
            return [item.strip() for item in payload.split(",") if item.strip()]
        return []

    def _coerce_score(self, payload: Any) -> float | None:
        """把相关性分数字段转换为浮点数。"""
        if payload is None or payload == "":
            return None
        try:
            return float(payload)
        except (TypeError, ValueError):
            return None

    def _build_citation_text(
        self,
        *,
        title: str,
        authors: list[str],
        year: str,
        venue: str,
        doi: str,
    ) -> str:
        """为外部候选生成默认引用文本。"""
        author_text = ", ".join(authors[:3]) if authors else "作者未知"
        venue_text = venue or "来源未知"
        year_text = year or "年份未知"
        citation = f"{author_text}. {title}. {venue_text}, {year_text}."
        if doi:
            citation = f"{citation} DOI: {doi}"
        return citation
