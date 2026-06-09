from __future__ import annotations

import re
from typing import Any

import config_data as config
from paper_source_mcp_server.providers.arxiv_provider import ArxivProvider
from paper_source_mcp_server.providers.base import ExternalPaperProvider
from paper_source_mcp_server.providers.openalex_provider import OpenAlexProvider
from paper_source_mcp_server.schemas import (
    ExternalPaperRecord,
    GetExternalPaperDetailArgs,
    ResolveExternalFulltextArgs,
    SearchExternalPapersArgs,
    build_tool_schemas,
)


class PaperSourceToolRegistry:
    """负责分发统一 MCP 工具到具体 provider 的工具路由层。"""

    def __init__(self, providers: dict[str, ExternalPaperProvider] | None = None) -> None:
        """初始化工具路由层，并注册可用 provider。"""
        self.providers = providers or {
            "arxiv": ArxivProvider(),
            "openalex": OpenAlexProvider(),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """返回当前服务建议暴露的 MCP 工具 schema。"""
        return build_tool_schemas()

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """按统一工具名分发请求，并返回标准化结果。"""
        if tool_name == "search_external_papers":
            return self.search_external_papers(self._build_search_args(arguments))
        if tool_name == "get_external_paper_detail":
            return self.get_external_paper_detail(GetExternalPaperDetailArgs(**arguments))
        if tool_name == "resolve_external_fulltext":
            return self.resolve_external_fulltext(ResolveExternalFulltextArgs(**arguments))
        raise ValueError(f"Unsupported tool name: {tool_name}")

    def search_external_papers(self, args: SearchExternalPapersArgs) -> dict[str, Any]:
        """执行多来源外部论文搜索，并合并返回结果。"""
        results: list[ExternalPaperRecord] = []
        errors: list[dict[str, str]] = []
        for source in args.sources:
            normalized_source = self._normalize_source_name(source)
            provider = self._require_provider(normalized_source)
            try:
                source_results = provider.search(
                    args.query,
                    limit=min(args.limit, config.MAX_EXTERNAL_QUERY_LIMIT),
                    date_from=args.date_from,
                    sortby=args.sortby,
                    orderby=args.orderby,
                )
            except Exception as exc:
                errors.append({"source": normalized_source, "message": str(exc)})
                continue
            results.extend(source_results)

        return {
            "results": [item.to_dict() for item in results],
            "errors": errors,
        }

    def get_external_paper_detail(self, args: GetExternalPaperDetailArgs) -> dict[str, Any]:
        """获取单篇外部论文的详细信息。"""
        provider = self._require_provider(args.source)
        result = provider.get_detail(args.external_id)
        return result.to_dict() if result is not None else {}

    def resolve_external_fulltext(self, args: ResolveExternalFulltextArgs) -> dict[str, Any]:
        """解析单篇外部论文可用的 PDF 或全文下载信息。"""
        provider = self._require_provider(args.source)
        record = ExternalPaperRecord(
            source=args.source,
            external_id=args.external_id,
            title=args.title,
            doi=args.doi,
            url=args.url,
            pdf_url=args.pdf_url,
        )
        result = provider.resolve_fulltext(record)
        return result.to_dict() if result is not None else {}

    def _require_provider(self, source: str) -> ExternalPaperProvider:
        """按来源名称获取 provider，不存在时抛出明确异常。"""
        provider = self.providers.get(self._normalize_source_name(source))
        if provider is None:
            raise ValueError(f"Unsupported source provider: {source}")
        return provider

    def _normalize_source_name(self, source: str) -> str:
        """把来源名称规范化为 provider 注册 key。"""
        return (source or "").strip().lower().replace("-", "_")

    def _build_search_args(self, arguments: dict[str, Any]) -> SearchExternalPapersArgs:
        """把 MCP 入参规范化为统一检索参数，并兼容少量旧字段。"""
        payload = dict(arguments)
        if "date_from" not in payload and payload.get("year_from") is not None:
            payload["date_from"] = f"{int(payload['year_from']):04d}0101"
        if "sortby" not in payload and payload.get("sort_by") is not None:
            payload["sortby"] = payload["sort_by"]
        if "orderby" not in payload and payload.get("sort_order") is not None:
            payload["orderby"] = payload["sort_order"]
        if "sources" not in payload and payload.get("source") is not None:
            payload["sources"] = [payload["source"]]

        return SearchExternalPapersArgs(
            query=self._normalize_query_keywords(payload.get("query")),
            limit=self._normalize_limit(payload.get("limit")),
            date_from=self._normalize_date_from(payload.get("date_from")),
            sortby=self._normalize_sortby(payload.get("sortby")),
            orderby=self._normalize_orderby(payload.get("orderby")),
            sources=self._normalize_sources(payload.get("sources")),
        )

    def _normalize_query_keywords(self, value: Any) -> list[str]:
        """规范化关键词列表；旧字符串会被拆成最多 4 个普通短语。"""
        if isinstance(value, list):
            raw_keywords = value
        else:
            raw_text = str(value or "")
            raw_text = raw_text.replace("all:", "").replace("ti:", "").replace("abs:", "").replace("au:", "")
            raw_text = re.sub(r"\b(?:AND|OR|NOT)\b", "|", raw_text, flags=re.IGNORECASE)
            raw_text = raw_text.replace("(", " ").replace(")", " ").replace('"', " ")
            raw_keywords = [item for item in re.split(r"[|,;，；、]", raw_text) if item.strip()]

        keywords: list[str] = []
        for item in raw_keywords:
            keyword = " ".join(str(item).split())
            if keyword and keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 4:
                break
        return keywords or ["paper"]

    def _normalize_limit(self, value: Any) -> int:
        """规范化单个数据源单次请求数量。"""
        try:
            limit = int(value)
        except (TypeError, ValueError):
            limit = config.MAX_EXTERNAL_QUERY_LIMIT
        return max(1, min(limit, config.MAX_EXTERNAL_QUERY_LIMIT))

    def _normalize_date_from(self, value: Any) -> str | None:
        """规范化 yyyymmdd 日期字符串。"""
        if value is None:
            return None
        normalized = re.sub(r"[^0-9]", "", str(value))
        if len(normalized) == 4:
            normalized = f"{normalized}0101"
        if len(normalized) != 8:
            return None
        return normalized

    def _normalize_sortby(self, value: Any) -> str:
        """规范化通用排序字段。"""
        normalized = str(value or "relevance").strip()
        if normalized not in {"relevance", "submittedDate", "publicationDate"}:
            return "relevance"
        return normalized

    def _normalize_orderby(self, value: Any) -> str:
        """规范化通用排序方向。"""
        normalized = str(value or "descending").strip()
        return normalized if normalized in {"descending", "ascending"} else "descending"

    def _normalize_sources(self, value: Any) -> list[str]:
        """规范化数据源列表，默认检索全部已支持数据源。"""
        if isinstance(value, list) and value:
            raw_sources = value
        elif isinstance(value, str) and value.strip():
            raw_sources = [value]
        else:
            raw_sources = ["arxiv", "openalex"]

        sources: list[str] = []
        for item in raw_sources:
            source = self._normalize_source_name(str(item))
            if source in self.providers and source not in sources:
                sources.append(source)
        return sources or ["arxiv", "openalex"]
