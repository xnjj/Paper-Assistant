from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import config_data as config
from app_backend.services.config_service import ConfigService


MAX_PARALLEL_EXTERNAL_QUERIES = config.MAX_PARALLEL_EXTERNAL_QUERIES
MAX_EXTERNAL_QUERY_LIMIT = config.MAX_EXTERNAL_QUERY_LIMIT
DEFAULT_EXTERNAL_FINAL_LIMIT = config.DEFAULT_EXTERNAL_FINAL_LIMIT


@dataclass
class ExternalSearchQueryPlan:
    """描述一次外部检索中的单条简单 query。"""

    query: str
    limit: int = MAX_EXTERNAL_QUERY_LIMIT
    year_from: int | None = None
    sort_by: str = "relevance"
    sort_order: str = "descending"
    sources: list[str] | None = None

    def to_search_kwargs(self) -> dict[str, Any]:
        """转换为 ExternalSearchService.search_papers 可以直接接收的参数。"""
        return {
            "query": self.query,
            "limit": self.limit,
            "year_from": self.year_from,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "sources": self.sources or ["arxiv"],
        }


@dataclass
class ExternalSearchPlan:
    """描述一次外部检索计划，内部可包含多条简单 query。"""

    queries: list[ExternalSearchQueryPlan]
    final_limit: int = DEFAULT_EXTERNAL_FINAL_LIMIT
    rationale: str = ""
    planned_by_model: bool = False

    def to_search_kwargs_list(self) -> list[dict[str, Any]]:
        """转换为批量外部检索服务可以直接接收的参数列表。"""
        return [query_plan.to_search_kwargs() for query_plan in self.queries]

    def to_dict(self) -> dict[str, Any]:
        """转换为可记录到 agent action 的字典。"""
        return asdict(self)


class ExternalSearchPlannerService:
    """使用 LLM 为外部论文检索生成多 query MCP 检索计划。"""

    def __init__(self, config_service: ConfigService | None = None) -> None:
        """保存运行时模型配置服务。"""
        self.config_service = config_service

    def plan(
        self,
        user_message: str,
        *,
        default_limit: int = DEFAULT_EXTERNAL_FINAL_LIMIT,
        freshness_requested: bool = False,
    ) -> ExternalSearchPlan:
        """根据用户问题生成外部检索计划，失败时返回规则兜底计划。"""
        fallback_plan = self._build_fallback_plan(
            user_message,
            default_limit=default_limit,
            freshness_requested=freshness_requested,
        )
        api_key = self._get_api_key()
        if not api_key:
            return fallback_plan

        try:
            response = self._build_openai_client(api_key).responses.create(
                model=self._get_model_name(),
                input=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_message},
                ],
                tools=self._build_function_tools(default_limit=default_limit),
            )
            function_call = self._extract_function_call(response)
            if function_call is None:
                return fallback_plan
            _, raw_arguments = function_call
            return self._normalize_plan(
                raw_arguments,
                fallback_plan=fallback_plan,
                default_limit=default_limit,
            )
        except Exception as exc:
            fallback_plan.rationale = f"{fallback_plan.rationale}; planner failed: {exc}"
            return fallback_plan

    def _build_openai_client(self, api_key: str) -> Any:
        """延迟导入 OpenAI SDK，并按模型名称选择默认兼容端点。"""
        from openai import OpenAI

        base_url = os.getenv("OPENAI_BASE_URL")
        model_name = self._get_model_name().lower()
        if not base_url and model_name.startswith(("qwen", "qwq")):
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        return OpenAI(api_key=api_key)

    def _build_system_prompt(self) -> str:
        """构造检索规划提示词。"""
        current_year = datetime.now().year
        return (
            "你是外部学术检索代理。"
            "当用户请求论文检索或研究现状时，必须调用 search_external_papers 工具生成检索计划。"
            f"当前年份是 {current_year}。"
            "对于“最近3年”这类时间条件，请换算 year_from。"
            f"请把复杂主题拆成最多 {MAX_PARALLEL_EXTERNAL_QUERIES} 条简单 arXiv query。"
            f"每条 query 的 limit 不超过 {MAX_EXTERNAL_QUERY_LIMIT}。"
            "少用 OR，避免复杂括号嵌套；每条 query 最多使用 2 个逻辑运算符。"
            "query 字段优先使用英文关键词和 arXiv 布尔表达式，"
            "例如 all:\"DQN\" AND all:\"autonomous driving\"。"
        )

    def _build_function_tools(self, *, default_limit: int) -> list[dict[str, Any]]:
        """定义让模型填充的批量 function tool schema。"""
        return [
            {
                "type": "function",
                "name": "search_external_papers",
                "description": (
                    "生成外部论文检索计划。请把复杂需求拆成多条简单 arXiv query，"
                    f"最多 {MAX_PARALLEL_EXTERNAL_QUERIES} 条，每条 limit 不超过 {MAX_EXTERNAL_QUERY_LIMIT}。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": MAX_PARALLEL_EXTERNAL_QUERIES,
                            "description": "需要并发执行的检索 query 列表。",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": (
                                            "arXiv 检索表达式。优先使用英文关键词和 all:\"...\" 前缀，"
                                            "例如 all:\"edge computing\" AND all:\"LLM\"。"
                                            "可使用 ti:, abs:, au:, cat:, all: 等前缀。"
                                            "推荐优先 AND，谨慎使用 OR，避免复杂括号嵌套。"
                                        ),
                                    },
                                    "year_from": {"type": "integer", "description": "起始年份，例如 2024。"},
                                    "sort_by": {
                                        "type": "string",
                                        "enum": ["relevance", "submittedDate"],
                                        "description": "排序字段。",
                                    },
                                    "sort_order": {
                                        "type": "string",
                                        "enum": ["descending", "ascending"],
                                        "description": "排序方向。",
                                    },
                                    "sources": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "检索源列表，目前优先使用 arxiv。",
                                    },
                                    "limit": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": MAX_EXTERNAL_QUERY_LIMIT,
                                        "description": f"单条 query 返回论文数量，建议 {min(default_limit, MAX_EXTERNAL_QUERY_LIMIT)}。",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                        "rationale": {
                            "type": "string",
                            "description": "简要说明为什么这样拆分检索 query。",
                        },
                    },
                    "required": ["queries"],
                },
            }
        ]

    def _extract_function_call(self, response: Any) -> tuple[str, dict[str, Any]] | None:
        """从 Responses API 返回值中提取 function_call 参数。"""
        output_items = getattr(response, "output", None) or []
        for item in output_items:
            if getattr(item, "type", "") != "function_call":
                continue
            tool_name = getattr(item, "name", "")
            raw_arguments = getattr(item, "arguments", "") or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                return None
            return tool_name, arguments
        return None

    def _normalize_plan(
        self,
        arguments: dict[str, Any],
        *,
        fallback_plan: ExternalSearchPlan,
        default_limit: int,
    ) -> ExternalSearchPlan:
        """校验模型生成的批量参数，非法字段回退到安全默认值。"""
        raw_queries = arguments.get("queries")
        query_items: list[Any]
        if isinstance(raw_queries, list) and raw_queries:
            query_items = raw_queries
        else:
            query_items = [arguments]

        fallback_query = fallback_plan.queries[0] if fallback_plan.queries else None
        common_fields = {
            key: value
            for key, value in arguments.items()
            if key in {"year_from", "sort_by", "sort_order", "sources", "limit"}
        }
        query_plans: list[ExternalSearchQueryPlan] = []
        seen_query_keys: set[str] = set()

        for item in query_items:
            if isinstance(item, str):
                candidate = {**common_fields, "query": item}
            elif isinstance(item, dict):
                candidate = {**common_fields, **item}
            else:
                continue

            query_plan = self._normalize_query_plan(
                candidate,
                fallback_query=fallback_query,
                default_limit=default_limit,
            )
            if query_plan is None:
                continue

            query_key = self._normalize_for_key(query_plan.query)
            if query_key in seen_query_keys:
                continue
            seen_query_keys.add(query_key)
            query_plans.append(query_plan)
            if len(query_plans) >= MAX_PARALLEL_EXTERNAL_QUERIES:
                break

        if not query_plans:
            return fallback_plan

        return ExternalSearchPlan(
            queries=query_plans,
            final_limit=self._normalize_limit(
                arguments.get("final_limit"),
                default=default_limit,
                max_limit=DEFAULT_EXTERNAL_FINAL_LIMIT,
                prefer_at_least_default=True,
            ),
            rationale=str(arguments.get("rationale") or "Planned by LLM function tool.").strip(),
            planned_by_model=True,
        )

    def _normalize_query_plan(
        self,
        arguments: dict[str, Any],
        *,
        fallback_query: ExternalSearchQueryPlan | None,
        default_limit: int,
    ) -> ExternalSearchQueryPlan | None:
        """把单条 query 参数规范化为安全的检索子计划。"""
        query = self._normalize_query_text(str(arguments.get("query") or "").strip())
        if not query:
            query = fallback_query.query if fallback_query is not None else ""
        if not query:
            return None

        year_from = self._normalize_year(
            arguments.get("year_from"),
            fallback_query.year_from if fallback_query is not None else None,
        )

        sort_by = str(arguments.get("sort_by") or (fallback_query.sort_by if fallback_query else "relevance")).strip()
        if sort_by not in {"relevance", "submittedDate"}:
            sort_by = fallback_query.sort_by if fallback_query else "relevance"

        sort_order = str(arguments.get("sort_order") or (fallback_query.sort_order if fallback_query else "descending")).strip()
        if sort_order not in {"descending", "ascending"}:
            sort_order = fallback_query.sort_order if fallback_query else "descending"

        sources = arguments.get("sources")
        if not isinstance(sources, list) or not sources:
            sources = fallback_query.sources if fallback_query is not None else ["arxiv"]
        sources = [str(item).strip() for item in sources if str(item).strip()] or ["arxiv"]

        return ExternalSearchQueryPlan(
            query=query,
            limit=self._normalize_limit(
                arguments.get("limit"),
                default=min(default_limit, MAX_EXTERNAL_QUERY_LIMIT),
                max_limit=MAX_EXTERNAL_QUERY_LIMIT,
            ),
            year_from=year_from,
            sort_by=sort_by,
            sort_order=sort_order,
            sources=sources,
        )

    def _build_fallback_plan(
        self,
        user_message: str,
        *,
        default_limit: int,
        freshness_requested: bool,
    ) -> ExternalSearchPlan:
        """模型规划不可用时的规则兜底计划。"""
        current_year = datetime.now().year
        query_plan = ExternalSearchQueryPlan(
            query=self._normalize_query_text(user_message.strip()) or "all:*",
            limit=self._normalize_limit(
                default_limit,
                default=MAX_EXTERNAL_QUERY_LIMIT,
                max_limit=MAX_EXTERNAL_QUERY_LIMIT,
            ),
            year_from=current_year - 2 if freshness_requested else None,
            sort_by="submittedDate" if freshness_requested else "relevance",
            sort_order="descending",
            sources=["arxiv"],
        )
        return ExternalSearchPlan(
            queries=[query_plan],
            final_limit=self._normalize_limit(
                default_limit,
                default=DEFAULT_EXTERNAL_FINAL_LIMIT,
                max_limit=DEFAULT_EXTERNAL_FINAL_LIMIT,
                prefer_at_least_default=True,
            ),
            rationale="Fallback search plan.",
            planned_by_model=False,
        )

    def _normalize_query_text(self, value: str) -> str:
        """清理模型可能生成的智能引号，避免 arXiv query 因符号异常而失效。"""
        return (
            value.replace("“", '"')
            .replace("”", '"')
            .replace("„", '"')
            .replace("‟", '"')
            .replace("＂", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("`", "'")
            .strip()
        )

    def _normalize_year(self, value: Any, fallback: int | None) -> int | None:
        """规范化年份字段。"""
        if isinstance(value, bool) or value is None:
            return fallback
        try:
            year = int(value)
        except (TypeError, ValueError):
            return fallback
        current_year = datetime.now().year
        if year < 1991 or year > current_year + 1:
            return fallback
        return year

    def _normalize_limit(
        self,
        value: Any,
        *,
        default: int,
        max_limit: int,
        prefer_at_least_default: bool = False,
    ) -> int:
        """规范化返回数量字段。"""
        try:
            limit = int(value)
        except (TypeError, ValueError):
            limit = int(default)
        if prefer_at_least_default:
            limit = max(limit, int(default))
        return max(1, min(limit, max_limit))

    def _normalize_for_key(self, value: str) -> str:
        """把 query 规整为适合去重比较的 key。"""
        return re.sub(r"\s+", " ", value.strip().lower())

    def _get_model_name(self) -> str:
        """读取当前 LLM 名称。"""
        if self.config_service is None:
            return "qwen3-max"
        return self.config_service.get_llm_model_name()

    def _get_api_key(self) -> str:
        """读取当前模型 API Key。"""
        if self.config_service is None:
            return os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
        return self.config_service.get_api_key() or os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
