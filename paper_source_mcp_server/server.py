from __future__ import annotations

import argparse
import os
from typing import Any

from paper_source_mcp_server.registry import PaperSourceToolRegistry

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    FastMCP = None  # type: ignore[assignment]


def build_fastmcp_server(
    server_name: str = "paper-source-mcp-server",
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    stateless_http: bool = True,
    json_response: bool = True,
    streamable_http_path: str = "/mcp",
) -> Any:
    """构造一个基于 FastMCP 的服务实例。

    这里使用可选导入，避免在尚未安装 MCP SDK 时影响项目其余部分运行。
    """
    if FastMCP is None:
        raise RuntimeError("FastMCP is not installed. Please install the MCP Python SDK first.")

    registry = PaperSourceToolRegistry()
    server = FastMCP(
        server_name,
        host=host,
        port=port,
        stateless_http=stateless_http,
        json_response=json_response,
        streamable_http_path=streamable_http_path,
    )

    @server.tool(
        name="search_external_papers",
        description="根据查询词搜索外部论文候选列表。",
    )
    def search_external_papers(
        query: list[str],
        limit: int = 10,
        date_from: str | None = None,
        sortby: str = "relevance",
        orderby: str = "descending",
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """暴露统一的外部论文搜索工具。"""
        return registry.call_tool(
            "search_external_papers",
            {
                "query": query,
                "limit": limit,
                "date_from": date_from,
                "sortby": sortby,
                "orderby": orderby,
                "sources": sources or ["arxiv", "openalex"],
            },
        )

    @server.tool(
        name="get_external_paper_detail",
        description="按来源和外部标识获取单篇论文详情。",
    )
    def get_external_paper_detail(source: str, external_id: str) -> dict[str, Any]:
        """暴露统一的外部论文详情工具。"""
        return registry.call_tool(
            "get_external_paper_detail",
            {
                "source": source,
                "external_id": external_id,
            },
        )

    @server.tool(
        name="resolve_external_fulltext",
        description="解析单篇论文可用的 PDF 或全文下载信息。",
    )
    def resolve_external_fulltext(
        source: str,
        external_id: str,
        title: str = "",
        doi: str = "",
        url: str = "",
        pdf_url: str = "",
    ) -> dict[str, Any]:
        """暴露统一的全文解析工具。"""
        return registry.call_tool(
            "resolve_external_fulltext",
            {
                "source": source,
                "external_id": external_id,
                "title": title,
                "doi": doi,
                "url": url,
                "pdf_url": pdf_url,
            },
        )

    return server


def build_argument_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="paper_source_mcp_server",
        description="启动统一外部论文检索 MCP Server。",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.getenv("PAPER_SOURCE_MCP_TRANSPORT", "stdio"),
        help="选择 MCP 传输方式，默认读取环境变量 PAPER_SOURCE_MCP_TRANSPORT，没有则使用 stdio。",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("PAPER_SOURCE_MCP_HOST", "127.0.0.1"),
        help="HTTP 传输监听地址，默认读取环境变量 PAPER_SOURCE_MCP_HOST。",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PAPER_SOURCE_MCP_PORT", "8000")),
        help="HTTP 传输监听端口，默认读取环境变量 PAPER_SOURCE_MCP_PORT。",
    )
    parser.add_argument(
        "--server-name",
        default=os.getenv("PAPER_SOURCE_MCP_NAME", "paper-source-mcp-server"),
        help="MCP 服务名称。",
    )
    parser.add_argument(
        "--streamable-http-path",
        default=os.getenv("PAPER_SOURCE_MCP_STREAMABLE_HTTP_PATH", "/mcp"),
        help="Streamable HTTP 模式下的挂载路径。",
    )
    parser.add_argument(
        "--stateful-http",
        action="store_true",
        help="启用有状态 HTTP 模式；默认使用官方推荐的无状态模式。",
    )
    parser.add_argument(
        "--non-json-response",
        action="store_true",
        help="关闭 JSON 响应模式，改用默认响应行为。",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """启动 MCP Server 的主入口。"""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    server = build_fastmcp_server(
        args.server_name,
        host=args.host,
        port=args.port,
        stateless_http=not args.stateful_http,
        json_response=not args.non_json_response,
        streamable_http_path=args.streamable_http_path,
    )
    server.run(transport=args.transport)


# 提供一个模块级默认实例，方便配合 `mcp run` / `mcp dev` 等工具使用。
if FastMCP is not None:  # pragma: no branch
    mcp = build_fastmcp_server()
else:  # pragma: no cover
    mcp = None


if __name__ == "__main__":
    main()
