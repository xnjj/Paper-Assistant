from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from langchain_community.chat_models import ChatTongyi

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
        """根据用户问题生成外部检索计划；LLM 失败时直接抛出异常，由上层终止流程。"""
        fallback_plan = self._build_fallback_plan(
            user_message,
            default_limit=default_limit,
            freshness_requested=freshness_requested,
        )
        response = self._build_model().invoke(
            self._build_planner_prompt(
                user_message,
                default_limit=default_limit,
                freshness_requested=freshness_requested,
            )
        )
        raw_arguments = self._parse_plan_arguments(self._extract_model_text(response))
        return self._normalize_plan(
            raw_arguments,
            fallback_plan=fallback_plan,
            default_limit=default_limit,
        )

    def _build_model(self) -> ChatTongyi:
        """根据当前运行时配置创建检索规划模型实例。"""
        model_name = self._get_model_name()
        api_key = self._get_api_key()
        return ChatTongyi(
            model=model_name,
            api_key=api_key or None,
            streaming=False,
        )

    def _build_system_prompt(self) -> str:
        """构造检索规划提示词。"""
        current_year = datetime.now().year
        return (
            "你是外部学术检索代理。"
            "当用户请求论文检索或研究现状时，必须生成可执行的外部检索计划。"
            f"当前年份是 {current_year}。"
            "对于明确时间限制条件（例如：最近x年），可以换算 date_from，格式必须是 yyyymmdd，如果没有时间限制，可为空。"
            f"请把复杂主题拆成最多 {MAX_PARALLEL_EXTERNAL_QUERIES} 组关键词。"
            f"每条 query 的 limit 不超过 {MAX_EXTERNAL_QUERY_LIMIT}。"
            "sources 字段默认同时使用 arxiv 和 openalex。"
            "arxiv 适合预印本和最新论文，openalex 适合按相关性做宽覆盖检索。"
            "query 字段只能输出英文关键词或短语数组，最多 4 个元素。"
            "不要输出 all:、AND、OR、cat:、search_query 等任何数据源专属语法。"
            "例如 [\"DQN\", \"autonomous driving\"]。"
        )

    def _build_planner_prompt(
        self,
        user_message: str,
        *,
        default_limit: int,
        freshness_requested: bool,
    ) -> str:
        """构造让 ChatTongyi 直接输出 JSON 检索计划的完整提示词。"""
        suggested_sortby = "submittedDate" if freshness_requested else "relevance"
        suggested_limit = min(default_limit, MAX_EXTERNAL_QUERY_LIMIT)
        return f"""
{self._build_system_prompt()}

请只输出一个 JSON 对象，不要输出 Markdown，不要输出解释性前后缀。
JSON 结构必须为：
{{
  "queries": [
    {{
      "query": ["英文关键词1", "英文关键词2"],
      "date_from": "yyyymmdd 或空字符串",
      "sortby": "relevance 或 submittedDate",
      "orderby": "descending 或 ascending",
      "sources": ["arxiv", "openalex"],
      "limit": {suggested_limit}
    }}
  ],
  "final_limit": {default_limit},
  "rationale": "一句中文说明检索计划"
}}

约束：
1. queries 最少 1 条，最多 {MAX_PARALLEL_EXTERNAL_QUERIES} 条。
2. 每条 query 最多 4 个英文关键词或英文短语。
3. limit 必须在 1 到 {MAX_EXTERNAL_QUERY_LIMIT} 之间。
4. sources 如果用户没有指定，使用 ["arxiv", "openalex"]。
5. sortby 默认使用 "{suggested_sortby}"，orderby 默认使用 "descending"。
6. 不要把 queries、query 或 sources 编码成字符串，必须直接输出数组。

用户问题：
{user_message}
""".strip()

    def _extract_model_text(self, response: Any) -> str:
        """从 ChatTongyi 响应中提取模型输出文本。"""
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "".join(parts)
        return str(content) if content else ""

    def _parse_plan_arguments(self, raw_text: str) -> dict[str, Any]:
        """从模型自然语言响应中解析第一个 JSON 对象。"""
        candidates = self._build_json_parse_candidates(raw_text)
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise ValueError("检索规划模型未返回可解析的 JSON 对象。")

    def _build_json_parse_candidates(self, raw_text: str) -> list[str]:
        """生成一组可能的 JSON 文本候选，兼容代码块和普通文本包裹。"""
        text = (raw_text or "").strip()
        candidates: list[str] = []
        if not text:
            return candidates

        fenced_matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
        candidates.extend(match.strip() for match in fenced_matches if match.strip())
        candidates.append(text)

        object_match = re.search(r"\{[\s\S]*\}", text)
        if object_match:
            candidates.append(object_match.group(0).strip())

        deduped: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    def _normalize_plan(
        self,
        arguments: dict[str, Any],
        *,
        fallback_plan: ExternalSearchPlan,
        default_limit: int,
    ) -> ExternalSearchPlan:
        """校验模型生成的批量参数，非法字段回退到安全默认值。"""
        arguments = self._coerce_json_object(arguments)
        raw_queries = self._coerce_json_value(arguments.get("queries"))
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
            item = self._coerce_json_value(item)
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
            raise ValueError("检索计划模型未生成可执行的 query。")

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
        arguments = self._normalize_query_aliases(arguments)
        query = self._normalize_query_keywords(arguments.get("query"))
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
        sources = self._coerce_json_value(sources)
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
        value = self._coerce_json_value(value)
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

    def _coerce_json_object(self, value: Any) -> dict[str, Any]:
        """把模型可能返回的 JSON 字符串参数安全转换为字典。"""
        value = self._coerce_json_value(value)
        return value if isinstance(value, dict) else {}

    def _coerce_json_value(self, value: Any) -> Any:
        """兼容模型把数组或对象字段二次编码成 JSON 字符串的情况。"""
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped or stripped[0] not in "[{":
            return value

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value

    def _normalize_query_aliases(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """兼容模型偶尔输出的字段别名，统一为内部检索计划字段。"""
        normalized = dict(arguments)
        if "query" not in normalized:
            for alias in ("queries", "keywords", "search_terms", "search_query"):
                if alias in normalized:
                    normalized["query"] = normalized[alias]
                    break
        if "sources" not in normalized and "source" in normalized:
            normalized["sources"] = normalized["source"]
        return normalized

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
