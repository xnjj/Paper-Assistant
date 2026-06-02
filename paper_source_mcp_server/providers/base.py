from __future__ import annotations

from typing import Protocol

from paper_source_mcp_server.schemas import ExternalFulltextRecord, ExternalPaperRecord


class ExternalPaperProvider(Protocol):
    """定义单个论文来源 provider 需要实现的统一接口。"""

    source_name: str

    def search(
        self,
        query: list[str],
        *,
        limit: int = 10,
        date_from: str | None = None,
        sortby: str = "relevance",
        orderby: str = "descending",
    ) -> list[ExternalPaperRecord]:
        """根据查询词搜索外部论文候选。"""
        ...

    def get_detail(self, external_id: str) -> ExternalPaperRecord | None:
        """按来源内部标识获取单篇论文详情。"""
        ...

    def resolve_fulltext(self, record: ExternalPaperRecord) -> ExternalFulltextRecord | None:
        """解析单篇论文可用的全文或 PDF 信息。"""
        ...
