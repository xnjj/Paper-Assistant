from __future__ import annotations

from typing import Any

from paper_source_mcp_server.providers.arxiv_provider import ArxivProvider
from paper_source_mcp_server.providers.base import ExternalPaperProvider
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
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """返回当前服务建议暴露的 MCP 工具 schema。"""
        return build_tool_schemas()

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """按统一工具名分发请求，并返回标准化结果。"""
        if tool_name == "search_external_papers":
            return self.search_external_papers(SearchExternalPapersArgs(**arguments))
        if tool_name == "get_external_paper_detail":
            return self.get_external_paper_detail(GetExternalPaperDetailArgs(**arguments))
        if tool_name == "resolve_external_fulltext":
            return self.resolve_external_fulltext(ResolveExternalFulltextArgs(**arguments))
        raise ValueError(f"Unsupported tool name: {tool_name}")

    def search_external_papers(self, args: SearchExternalPapersArgs) -> dict[str, Any]:
        """执行多来源外部论文搜索，并合并返回结果。"""
        results: list[ExternalPaperRecord] = []
        for source in args.sources:
            provider = self._require_provider(source)
            results.extend(
                provider.search(
                    args.query,
                    limit=args.limit,
                    year_from=args.year_from,
                    sort_by=args.sort_by,
                    sort_order=args.sort_order,
                )
            )

        return {
            "results": [item.to_dict() for item in results[: args.limit]],
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
        provider = self.providers.get(source)
        if provider is None:
            raise ValueError(f"Unsupported source provider: {source}")
        return provider
