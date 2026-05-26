from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path
from typing import Any


class StdioMCPToolInvoker:
    """通过 stdio 启动独立 MCP Server，并同步调用指定工具。"""

    def __init__(
        self,
        *,
        command: str | None = None,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """保存 MCP Server 启动参数，实际子进程会在每次工具调用时创建。"""
        project_root = Path(__file__).resolve().parents[2]
        self.command = command or sys.executable
        self.args = args or ["-m", "paper_source_mcp_server", "--transport", "stdio"]
        self.cwd = cwd or str(project_root)
        self.env = self._build_environment(project_root, env)
        self.timeout_seconds = timeout_seconds

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """同步调用一个 MCP tool，并返回结构化结果。"""
        return self._run_async_safely(self._call_tool_async(tool_name, arguments))

    async def _call_tool_async(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """在异步上下文中启动 stdio server、初始化会话并执行工具调用。"""
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        server_parameters = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
            cwd=self.cwd,
            encoding="utf-8",
            encoding_error_handler="replace",
        )

        async with stdio_client(server_parameters) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
        return self._extract_structured_payload(result)

    def _run_async_safely(self, coroutine: Any) -> Any:
        """在同步代码中运行异步 MCP 调用，兼容 FastAPI 已有事件循环场景。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._with_optional_timeout(coroutine))

        result_box: dict[str, Any] = {}
        error_box: dict[str, BaseException] = {}

        def runner() -> None:
            """在线程中运行异步调用，避免嵌套当前事件循环。"""
            try:
                result_box["result"] = asyncio.run(self._with_optional_timeout(coroutine))
            except BaseException as exc:  # pragma: no cover
                error_box["error"] = exc

        thread = threading.Thread(target=runner, name="stdio-mcp-tool-call", daemon=True)
        thread.start()
        thread.join()
        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("result")

    async def _with_optional_timeout(self, coroutine: Any) -> Any:
        """按需给 MCP 工具调用增加整体超时。"""
        if self.timeout_seconds is None:
            return await coroutine
        return await asyncio.wait_for(coroutine, timeout=self.timeout_seconds)

    def _extract_structured_payload(self, result: Any) -> dict[str, Any]:
        """从 MCP 调用结果中提取结构化返回体，并把工具错误转成异常。"""
        if bool(getattr(result, "isError", False)) or bool(getattr(result, "is_error", False)):
            error_message = self._extract_tool_error_message(result)
            raise RuntimeError(f"MCP tool call failed: {error_message or result!r}")

        structured_payload = getattr(result, "structuredContent", None)
        if isinstance(structured_payload, dict):
            return structured_payload

        structured_payload = getattr(result, "structured_content", None)
        if isinstance(structured_payload, dict):
            return structured_payload

        error_message = self._extract_tool_error_message(result)
        if error_message:
            raise RuntimeError(f"MCP tool did not return structured content: {error_message}")
        raise RuntimeError("MCP tool did not return structured content.")

    def _extract_tool_error_message(self, result: Any) -> str:
        """尽量从 MCP 返回对象中提取可读的错误文本。"""
        content_items = getattr(result, "content", None)
        if not isinstance(content_items, list):
            return ""

        text_fragments: list[str] = []
        for item in content_items:
            text_value = getattr(item, "text", None)
            if isinstance(text_value, str) and text_value.strip():
                text_fragments.append(text_value.strip())
        return " | ".join(text_fragments)

    def _build_environment(self, project_root: Path, overrides: dict[str, str] | None) -> dict[str, str]:
        """构造子进程环境变量，并确保项目根目录位于 PYTHONPATH。"""
        env = dict(os.environ)
        existing_pythonpath = env.get("PYTHONPATH", "")
        pythonpath_parts = [str(project_root)]
        if existing_pythonpath:
            pythonpath_parts.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
        if overrides:
            env.update(overrides)
        return env
