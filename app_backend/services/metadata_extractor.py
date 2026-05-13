from __future__ import annotations

import json
import logging
import re

from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app_backend.models import ExtractedMetadata, ParsedDocument

logger = logging.getLogger(__name__)


class MetadataExtractorService:
    """元数据抽取层。

    当前版本主要使用 LLM 从解析文本中抽取标题、摘要和关键词。
    后续可以在这里继续补充作者、年份、DOI、期刊等字段的规则或工具调用。
    """

    def __init__(self) -> None:
        """初始化元数据抽取器。"""
        self.model = ChatTongyi(model="qwen3-max")

    def extract(self, parsed_document: ParsedDocument) -> ExtractedMetadata:
        """从解析后的文档中抽取结构化元数据。

        Args:
            parsed_document: PDF 解析层输出的标准化文档对象。

        Returns:
            ExtractedMetadata: 标题、摘要、关键词等结构化结果。
        """
        text_for_llm = parsed_document.raw_text[:18000]
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是学术论文信息抽取助手。"
                    "请从给定论文文本中提取 title、abstract、keywords。"
                    "只输出 JSON，不要输出任何解释。"
                    "JSON schema: {{\"title\": str, \"abstract\": str, \"keywords\": [str, ...]}}"
                ),
                (
                    "human",
                    "请提取以下论文文本中的标题、摘要和关键词：\n\n"
                    "{text}\n\n"
                    "注意：\n"
                    "1) 若标题不确定，选择最像论文题目的那一行；\n"
                    "2) 摘要尽量完整、连贯；\n"
                    "3) 关键词最多输出 10 个；\n"
                    "4) 若缺失字段，使用空字符串或空数组。",
                ),
            ]
        )

        chain = prompt | self.model | StrOutputParser()
        raw = chain.invoke({"text": text_for_llm}).strip()

        try:
            match = re.search(r"\{[\s\S]*\}", raw)
            payload = json.loads(match.group(0) if match else raw)
            title = str(payload.get("title", "")).strip() or PathFallback.name_without_suffix(parsed_document.file_name)
            abstract = str(payload.get("abstract", "")).strip() or "（未提取到摘要）"
            keywords = self._normalize_keywords(payload.get("keywords", []))
            return ExtractedMetadata(title=title, abstract=abstract, keywords=keywords)
        except Exception as exc:
            logger.warning("元数据抽取失败，回退到默认值: %s", exc)
            return ExtractedMetadata(
                title=PathFallback.name_without_suffix(parsed_document.file_name),
                abstract="（未提取到摘要）",
                keywords=[],
            )

    def _normalize_keywords(self, keywords: object) -> list[str]:
        """清洗关键词列表。

        Args:
            keywords: LLM 返回的原始关键词对象。

        Returns:
            list[str]: 去重、去空白并限制数量后的关键词列表。
        """
        if not isinstance(keywords, list):
            return []

        cleaned_keywords: list[str] = []
        seen = set()
        for keyword in keywords:
            cleaned = re.sub(r"\s+", " ", str(keyword)).strip(" \t\r\n,;，；")
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned_keywords.append(cleaned)
            if len(cleaned_keywords) >= 10:
                break
        return cleaned_keywords


class PathFallback:
    """处理文件名回退逻辑的小工具类。"""

    @staticmethod
    def name_without_suffix(file_name: str) -> str:
        """去掉文件扩展名，作为默认标题。

        Args:
            file_name: 原始文件名。

        Returns:
            str: 去除扩展名后的文件名。
        """
        if "." not in file_name:
            return file_name
        return file_name.rsplit(".", 1)[0]
