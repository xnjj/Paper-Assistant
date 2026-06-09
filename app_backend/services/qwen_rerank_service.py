from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

import config_data as config

if TYPE_CHECKING:
    from app_backend.services.config_service import ConfigService


@dataclass(frozen=True)
class QwenRerankResult:
    """qwen3-rerank 返回的单条重排结果。"""

    index: int
    relevance_score: float


class QwenRerankService:
    """通过 DashScope HTTP API 调用 qwen3-rerank。"""

    def __init__(self, config_service: ConfigService) -> None:
        """保存配置服务，运行时从数据库读取 API_KEY。"""
        self.config_service = config_service

    def rerank(self, *, query: str, documents: list[str], top_n: int) -> list[QwenRerankResult]:
        """调用 qwen3-rerank 并返回按相关性排序后的结果。"""
        if not documents:
            return []

        payload = {
            "model": config.RERANK_MODEL_NAME,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": max(1, min(int(top_n), len(documents))),
                "return_documents": False,
                "instruct": config.RERANK_INSTRUCTION,
            },
        }
        request = urllib.request.Request(
            config.QWEN_RERANK_ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config_service.get_api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=config.RERANK_TIMEOUT_SECONDS) as response:
                raw_payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"qwen3-rerank HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"qwen3-rerank 连接失败：{exc}") from exc

        response_payload = json.loads(raw_payload)
        raw_results = response_payload.get("output", {}).get("results", [])
        if not isinstance(raw_results, list):
            raise RuntimeError("qwen3-rerank 返回结构中缺少 output.results。")

        results: list[QwenRerankResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            try:
                index = int(item.get("index"))
                score = float(item.get("relevance_score"))
            except (TypeError, ValueError):
                continue
            if 0 <= index < len(documents):
                results.append(QwenRerankResult(index=index, relevance_score=score))
        return results
