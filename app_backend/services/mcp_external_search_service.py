from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from typing import Any, Protocol

import config_data as config
from app_backend.services.citation_formatter import format_gbt7714_citation
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
        limit: int = config.MAX_EXTERNAL_QUERY_LIMIT,
        year_from: int | None = None,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        sources: list[str] | None = None,
    ) -> list[ExternalPaperCandidate]:
        """调用 MCP 检索工具获取外部论文候选。"""
        if self.tool_invoker is None:
            return []

        arguments = {
            "query": query,
            "limit": limit,
            "year_from": year_from,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "sources": sources or [self.default_source],
        }
        try:
            raw_result = self.tool_invoker.call_tool(self.search_tool_name, arguments)
        except Exception as exc:
            if not self._is_rate_limit_error(exc):
                print(f"MCP external search failed: {exc}")
                return []

            fallback_arguments = {
                **arguments,
                "limit": min(5, int(limit or config.MAX_EXTERNAL_QUERY_LIMIT)),
                "year_from": None,
                "sort_by": "relevance",
            }
            try:
                raw_result = self.tool_invoker.call_tool(self.search_tool_name, fallback_arguments)
            except Exception as fallback_exc:
                print(f"MCP external search failed after fallback: {fallback_exc}")
                return []

        candidates = self._coerce_candidate_list(raw_result)
        for candidate in candidates:
            candidate.matched_query = query
        return candidates

    def search_papers_batch(
        self,
        query_plans: list[dict[str, Any]],
        *,
        final_limit: int = config.DEFAULT_EXTERNAL_FINAL_LIMIT,
    ) -> list[ExternalPaperCandidate]:
        """并发执行多条 MCP 检索，并对候选论文合并去重。"""
        if self.tool_invoker is None or not query_plans:
            return []

        safe_plans = query_plans[: config.MAX_PARALLEL_EXTERNAL_QUERIES]
        results_by_index: dict[int, list[ExternalPaperCandidate]] = {}
        max_workers = min(config.MAX_PARALLEL_EXTERNAL_QUERIES, max(1, len(safe_plans)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_plan = {
                executor.submit(self.search_papers, **query_plan): (index, query_plan)
                for index, query_plan in enumerate(safe_plans)
            }
            for future in as_completed(future_to_plan):
                index, query_plan = future_to_plan[future]
                try:
                    results_by_index[index] = future.result()
                except Exception as exc:  # pragma: no cover - 外部服务异常以日志为主
                    print(f"MCP external batch search failed for {query_plan.get('query')}: {exc}")
                    results_by_index[index] = []

        ordered_candidates: list[ExternalPaperCandidate] = []
        for index in range(len(safe_plans)):
            ordered_candidates.extend(results_by_index.get(index, []))

        return self._dedupe_candidates(ordered_candidates)[: max(1, min(final_limit, config.DEFAULT_EXTERNAL_FINAL_LIMIT))]

    def iter_search_papers_batch(
        self,
        query_plans: list[dict[str, Any]],
        *,
        final_limit: int = config.DEFAULT_EXTERNAL_FINAL_LIMIT,
    ) -> Iterator[dict[str, Any]]:
        """以事件形式并发执行多条 MCP 检索，便于前端展示准备进度。"""
        if self.tool_invoker is None or not query_plans:
            yield {
                "type": "search_batch_done",
                "candidates": [],
                "raw_count": 0,
                "deduped_count": 0,
            }
            return

        safe_plans = query_plans[: config.MAX_PARALLEL_EXTERNAL_QUERIES]
        results_by_index: dict[int, list[ExternalPaperCandidate]] = {}
        max_workers = min(config.MAX_PARALLEL_EXTERNAL_QUERIES, max(1, len(safe_plans)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_plan = {}
            for index, query_plan in enumerate(safe_plans):
                query_id = self._build_query_step_id(index)
                yield {
                    "type": "search_query_start",
                    "query_id": query_id,
                    **self._build_query_event_payload(query_plan),
                }
                future = executor.submit(self.search_papers, **query_plan)
                future_to_plan[future] = (index, query_id, query_plan)

            for future in as_completed(future_to_plan):
                index, query_id, query_plan = future_to_plan[future]
                try:
                    candidates = future.result()
                    results_by_index[index] = candidates
                    yield {
                        "type": "search_query_done",
                        "query_id": query_id,
                        "result_count": len(candidates),
                        **self._build_query_event_payload(query_plan),
                    }
                except Exception as exc:  # pragma: no cover - 外部服务异常以日志为主
                    results_by_index[index] = []
                    yield {
                        "type": "search_query_error",
                        "query_id": query_id,
                        "error": str(exc),
                        **self._build_query_event_payload(query_plan),
                    }

        ordered_candidates: list[ExternalPaperCandidate] = []
        for index in range(len(safe_plans)):
            ordered_candidates.extend(results_by_index.get(index, []))
        deduped_candidates = self._dedupe_candidates(ordered_candidates)
        limited_candidates = deduped_candidates[: max(1, min(final_limit, config.DEFAULT_EXTERNAL_FINAL_LIMIT))]

        yield {
            "type": "search_batch_done",
            "candidates": limited_candidates,
            "raw_count": len(ordered_candidates),
            "deduped_count": len(deduped_candidates),
        }

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
                url=url,
                source=source,
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
        url: str,
        source: str,
    ) -> str:
        """为外部候选生成近似 GB/T 7714-2015 的默认引用文本。"""
        return format_gbt7714_citation(
            authors=authors,
            title=title,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            source_type=source or "external",
        )

    def _dedupe_candidates(self, candidates: list[ExternalPaperCandidate]) -> list[ExternalPaperCandidate]:
        """按来源 ID、URL、标题逐级去重外部候选。"""
        deduped: list[ExternalPaperCandidate] = []
        seen_keys: set[str] = set()
        for candidate in candidates:
            key = self._build_candidate_unique_key(candidate)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(candidate)
        return deduped

    def _build_candidate_unique_key(self, candidate: ExternalPaperCandidate) -> str:
        """构造外部候选论文的去重键。"""
        source = (candidate.source or "").strip().lower()
        external_id = (candidate.external_id or "").strip().lower()
        if source and external_id:
            return f"{source}:{external_id}"

        url = (candidate.url or "").strip().lower()
        if url:
            return f"url:{url.rstrip('/')}"

        title = self._normalize_for_key(candidate.title)
        return f"title:{title}" if title else ""

    def _normalize_for_key(self, value: str) -> str:
        """把字符串规整为适合比较的 key。"""
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        """判断异常是否属于外部检索限流。"""
        message = str(exc).lower()
        return "429" in message or "too many requests" in message

    def _build_query_step_id(self, index: int) -> str:
        """为一条并发检索 query 构造前端可稳定更新的步骤 ID。"""
        return f"external-query-{index + 1}"

    def _build_query_event_payload(self, query_plan: dict[str, Any]) -> dict[str, Any]:
        """把检索 query 参数转换为前端准备区事件载荷。"""
        sources = query_plan.get("sources")
        if not isinstance(sources, list) or not sources:
            sources = [self.default_source]
        source_text = ", ".join(str(item).strip() for item in sources if str(item).strip())
        return {
            "source": source_text or self.default_source,
            "query": str(query_plan.get("query") or ""),
            "sort_by": str(query_plan.get("sort_by") or "relevance"),
            "sort_order": str(query_plan.get("sort_order") or "descending"),
        }
