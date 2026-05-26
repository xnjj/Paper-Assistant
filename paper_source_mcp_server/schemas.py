from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExternalPaperRecord:
    """描述统一格式的外部论文记录。"""

    source: str
    external_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    pdf_url: str = ""
    relevance_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """把论文记录转换为字典。"""
        return asdict(self)


@dataclass
class ExternalFulltextRecord:
    """描述外部论文的全文或 PDF 信息。"""

    source: str
    external_id: str
    title: str
    pdf_url: str = ""
    download_url: str = ""
    landing_page_url: str = ""
    content_type: str = ""
    license: str = ""
    is_open_access: bool = False

    def to_dict(self) -> dict[str, Any]:
        """把全文记录转换为字典。"""
        return asdict(self)


@dataclass
class SearchExternalPapersArgs:
    """定义 `search_external_papers` 工具的输入参数。"""

    query: str
    limit: int = 10
    year_from: int | None = None
    sort_by: str = "relevance"
    sort_order: str = "descending"
    sources: list[str] = field(default_factory=lambda: ["arxiv"])


@dataclass
class GetExternalPaperDetailArgs:
    """定义 `get_external_paper_detail` 工具的输入参数。"""

    source: str
    external_id: str


@dataclass
class ResolveExternalFulltextArgs:
    """定义 `resolve_external_fulltext` 工具的输入参数。"""

    source: str
    external_id: str
    title: str = ""
    doi: str = ""
    url: str = ""
    pdf_url: str = ""


def build_tool_schemas() -> list[dict[str, Any]]:
    """返回推荐给 MCP Server 暴露的统一工具 schema。"""
    return [
        {
            "name": "search_external_papers",
            "description": "根据查询词搜索外部论文候选列表。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "用户查询词"},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                    "year_from": {"type": ["integer", "null"], "description": "年份下限"},
                    "sort_by": {
                        "type": "string",
                        "default": "relevance",
                        "description": "排序字段，例如 relevance 或 submittedDate",
                    },
                    "sort_order": {
                        "type": "string",
                        "default": "descending",
                        "description": "排序顺序，例如 ascending 或 descending",
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["arxiv"],
                        "description": "需要检索的外部来源列表",
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_external_paper_detail",
            "description": "按来源和外部标识获取单篇论文详情。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "外部来源名称，如 arxiv"},
                    "external_id": {"type": "string", "description": "来源内部的论文标识"},
                },
                "required": ["source", "external_id"],
            },
        },
        {
            "name": "resolve_external_fulltext",
            "description": "解析单篇论文可用的 PDF 或全文下载信息。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "外部来源名称，如 arxiv"},
                    "external_id": {"type": "string", "description": "来源内部的论文标识"},
                    "title": {"type": "string", "default": ""},
                    "doi": {"type": "string", "default": ""},
                    "url": {"type": "string", "default": ""},
                    "pdf_url": {"type": "string", "default": ""},
                },
                "required": ["source", "external_id"],
            },
        },
    ]
