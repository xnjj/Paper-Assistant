from __future__ import annotations

from collections.abc import Callable
from threading import BoundedSemaphore
from typing import TypeVar

import config_data as config

T = TypeVar("T")


class LLMConcurrencyLimiter:
    """统一限制项目内所有 LLM 调用的并发数量。"""

    def __init__(self, max_concurrency: int | None = None) -> None:
        """初始化全局 LLM 并发限制器。"""
        resolved_max = max_concurrency or config.MAX_PARALLEL_LLM_QUERIES
        self.max_concurrency = max(1, int(resolved_max))
        self._semaphore = BoundedSemaphore(self.max_concurrency)

    def run(self, action: Callable[[], T]) -> T:
        """在获取并发许可后执行一次 LLM 调用。"""
        with self._semaphore:
            return action()
