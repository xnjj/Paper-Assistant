from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ExternalPaperCandidate:
    """描述一次外部检索返回的候选论文。"""

    source: str
    external_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    citation_text_default: str = ""
    pdf_url: str | None = None
    relevance_score: float | None = None


@dataclass
class ExternalFulltextPayload:
    """描述外部候选文献可用的全文或 PDF 信息。"""

    source: str
    external_id: str
    title: str
    pdf_url: str = ""
    download_url: str = ""
    landing_page_url: str = ""
    content_type: str = ""
    license: str = ""
    is_open_access: bool = False


class ExternalSearchService(Protocol):
    """定义外部检索服务需要满足的最小接口。"""

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 10,
        year_from: int | None = None,
    ) -> list[ExternalPaperCandidate]:
        """根据查询词搜索外部论文候选。"""
        ...

    def get_paper_detail(self, external_id: str) -> ExternalPaperCandidate | None:
        """按外部标识获取单篇论文的详细信息。"""
        ...

    def resolve_fulltext(self, candidate: ExternalPaperCandidate) -> ExternalFulltextPayload | None:
        """尝试解析候选论文的全文或 PDF 下载信息。"""
        ...


class NullExternalSearchService:
    """空实现，用于在未接入真实外部检索时保持主链路可运行。"""

    def search_papers(
        self,
        query: str,
        *,
        limit: int = 10,
        year_from: int | None = None,
    ) -> list[ExternalPaperCandidate]:
        """默认不返回任何外部候选。"""
        return []

    def get_paper_detail(self, external_id: str) -> ExternalPaperCandidate | None:
        """默认不提供任何外部详情。"""
        return None

    def resolve_fulltext(self, candidate: ExternalPaperCandidate) -> ExternalFulltextPayload | None:
        """默认不解析全文。"""
        return None
