from __future__ import annotations

import json
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

    query: list[str]
    limit: int = MAX_EXTERNAL_QUERY_LIMIT
    date_from: str | None = None
    sortby: str = "relevance"
    orderby: str = "descending"
    sources: list[str] | None = None

    def to_search_kwargs(self) -> dict[str, Any]:
        """转换为 ExternalSearchService.search_papers 可以直接接收的参数。"""
        return {
            "query": self.query,
            "limit": self.limit,
            "date_from": self.date_from,
            "sortby": self.sortby,
            "orderby": self.orderby,
            "sources": self.sources or ["arxiv", "openalex"],
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
            "对于“最近3年”这类时间条件，请换算 date_from，格式必须是 yyyymmdd。"
            f"请把复杂主题拆成最多 {MAX_PARALLEL_EXTERNAL_QUERIES} 组关键词。"
            f"每条 query 的 limit 不超过 {MAX_EXTERNAL_QUERY_LIMIT}。"
            "sources 字段默认同时使用 arxiv 和 openalex。"
            "arxiv 适合预印本和最新论文，openalex 适合按相关性做宽覆盖检索。"
            "query 字段只能输出英文关键词或短语数组，最多 4 个元素。"
            "不要输出 all:、AND、OR、cat:、search_query 等任何数据源专属语法。"
            "例如 [\"DQN\", \"autonomous driving\"]。"
        )

    def _build_function_tools(self, *, default_limit: int) -> list[dict[str, Any]]:
        """定义让模型填充的批量 function tool schema。"""
        return [
            {
                "type": "function",
                "name": "search_external_papers",
                "description": (
                    "生成外部论文检索计划。请把复杂需求拆成多组关键词，"
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
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 1,
                                        "maxItems": 4,
                                        "description": (
                                            "检索关键词或短语数组，最多 4 个。"
                                            "不要包含 all:、AND、OR、cat: 等数据源语法。"
                                            "例如 [\"edge computing\", \"LLM inference\"]。"
                                        ),
                                    },
                                    "date_from": {
                                        "type": "string",
                                        "description": "日期下限，格式 yyyymmdd，例如 20240101。",
                                    },
                                    "sortby": {
                                        "type": "string",
                                        "enum": ["relevance", "submittedDate"],
                                        "description": "排序字段。",
                                    },
                                    "orderby": {
                                        "type": "string",
                                        "enum": ["descending", "ascending"],
                                        "description": "排序方向。",
                                    },
                                    "sources": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "检索源列表，可使用 arxiv、openalex；默认两者都使用。",
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
            if key in {"date_from", "sortby", "orderby", "sources", "limit"}
        }
        query_plans: list[ExternalSearchQueryPlan] = []
        seen_query_keys: set[str] = set()

        for item in query_items:
            if isinstance(item, str):
                candidate = {**common_fields, "query": [item]}
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

            query_key = self._normalize_for_key(" ".join(query_plan.query))
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
        query = self._normalize_query_keywords(arguments.get("query"))
        if not query:
            query = fallback_query.query if fallback_query is not None else []
        if not query:
            return None

        date_from = self._normalize_date_from(
            arguments.get("date_from"),
            fallback_query.date_from if fallback_query is not None else None,
        )

        sortby = str(arguments.get("sortby") or (fallback_query.sortby if fallback_query else "relevance")).strip()
        if sortby not in {"relevance", "submittedDate"}:
            sortby = fallback_query.sortby if fallback_query else "relevance"

        orderby = str(arguments.get("orderby") or (fallback_query.orderby if fallback_query else "descending")).strip()
        if orderby not in {"descending", "ascending"}:
            orderby = fallback_query.orderby if fallback_query else "descending"

        sources = arguments.get("sources")
        if not isinstance(sources, list) or not sources:
            sources = fallback_query.sources if fallback_query is not None else ["arxiv", "openalex"]
        sources = self._normalize_sources(sources)

        return ExternalSearchQueryPlan(
            query=query,
            limit=self._normalize_limit(
                arguments.get("limit"),
                default=min(default_limit, MAX_EXTERNAL_QUERY_LIMIT),
                max_limit=MAX_EXTERNAL_QUERY_LIMIT,
            ),
            date_from=date_from,
            sortby=sortby,
            orderby=orderby,
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
            query=self._build_fallback_keywords(user_message),
            limit=self._normalize_limit(
                default_limit,
                default=MAX_EXTERNAL_QUERY_LIMIT,
                max_limit=MAX_EXTERNAL_QUERY_LIMIT,
            ),
            date_from=f"{current_year - 2}0101" if freshness_requested else None,
            sortby="submittedDate" if freshness_requested else "relevance",
            orderby="descending",
            sources=["arxiv", "openalex"],
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

    def _normalize_query_keywords(self, value: Any) -> list[str]:
        """规范化模型返回的关键词数组，兼容旧字符串输出并限制最多 4 个关键词。"""
        if isinstance(value, list):
            raw_keywords = value
        else:
            raw_text = self._normalize_text(str(value or ""))
            raw_text = raw_text.replace("all:", "").replace("ti:", "").replace("abs:", "").replace("au:", "")
            raw_text = re.sub(r"\b(?:AND|OR|NOT)\b", "|", raw_text, flags=re.IGNORECASE)
            raw_text = raw_text.replace("(", " ").replace(")", " ").replace('"', " ")
            raw_keywords = [item for item in re.split(r"[|,;，；、]", raw_text) if item.strip()]

        keywords: list[str] = []
        for item in raw_keywords:
            keyword = self._normalize_text(str(item))
            if keyword and keyword not in keywords:
                keywords.append(keyword)
            if len(keywords) >= 4:
                break
        return keywords

    def _build_fallback_keywords(self, user_message: str) -> list[str]:
        """模型规划不可用时，从用户问题中构造保守关键词。"""
        normalized = self._normalize_text(user_message)
        if not normalized:
            return ["paper"]

        quoted_phrases = re.findall(r"[“\"]([^”\"]{2,80})[”\"]", normalized)
        keywords: list[str] = []
        for phrase in quoted_phrases:
            cleaned = self._normalize_text(phrase)
            if cleaned and cleaned not in keywords:
                keywords.append(cleaned)

        ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9 -]{1,48}", normalized)
        for term in ascii_terms:
            cleaned = self._normalize_text(term)
            if cleaned and cleaned.lower() not in {"and", "or", "the", "for"} and cleaned not in keywords:
                keywords.append(cleaned)
            if len(keywords) >= 4:
                break

        return keywords[:4] or [normalized[:80]]

    def _normalize_date_from(self, value: Any, fallback: str | None) -> str | None:
        """规范化 yyyymmdd 日期字段。"""
        if isinstance(value, bool) or value is None:
            return fallback
        normalized = re.sub(r"[^0-9]", "", str(value))
        if len(normalized) == 4:
            normalized = f"{normalized}0101"
        if len(normalized) != 8:
            return fallback
        try:
            datetime.strptime(normalized, "%Y%m%d")
        except ValueError:
            return fallback
        return normalized

    def _normalize_text(self, value: str) -> str:
        """清理模型可能生成的智能引号和多余空白。"""
        normalized = (
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
        return re.sub(r"\s+", " ", normalized)

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

    def _normalize_sources(self, values: list[Any]) -> list[str]:
        """规范化模型返回的数据源列表，只保留当前已支持的数据源。"""
        supported_sources = {"arxiv", "openalex"}
        sources: list[str] = []
        for item in values:
            source = str(item).strip().lower().replace("-", "_")
            if source in supported_sources and source not in sources:
                sources.append(source)
        return sources or ["arxiv", "openalex"]

    def _get_model_name(self) -> str:
        """读取当前 LLM 名称。"""
        if self.config_service is None:
            raise ValueError("模型配置服务未初始化，请先完成模型配置。")
        return self.config_service.get_llm_model_name()

    def _get_api_key(self) -> str:
        """读取当前模型 API Key。"""
        if self.config_service is None:
            raise ValueError("模型配置服务未初始化，请先完成模型配置。")
        return self.config_service.get_api_key()
