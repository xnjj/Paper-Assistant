from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz

from app_backend.models import ParsedDocument


class PDFParserService:
    """PDF 解析层。

    该层只负责读取 PDF、抽取文本和计算文件哈希，
    不承担 LLM 元数据抽取、数据库写入或向量索引工作。
    """

    def parse(self, file_path: str) -> ParsedDocument:
        """解析单个 PDF 文件。

        Args:
            file_path: 本地 PDF 的绝对路径或相对路径。

        Returns:
            ParsedDocument: 供后续元数据抽取和入库使用的标准化解析结果。
        """
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"文件不存在: {path}")

        file_hash = self._compute_file_hash(path)
        raw_text, page_count = self._extract_relevant_text(path)
        if not raw_text:
            raise ValueError("PDF 文本为空，可能是扫描件或受保护文档。")

        return ParsedDocument(
            file_path=str(path),
            file_name=path.name,
            file_hash=file_hash,
            raw_text=raw_text,
            page_count=page_count,
        )

    def _compute_file_hash(self, file_path: Path) -> str:
        """计算文件内容的 SHA256 哈希。

        Args:
            file_path: 待计算哈希的文件路径。

        Returns:
            str: 文件内容哈希值。
        """
        digest = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _extract_relevant_text(self, file_path: Path) -> tuple[str, int]:
        """优先抽取摘要前后的关键页面文本。

        策略说明：
        - 如果在前几页发现 `abstract/摘要`，则提取到该页为止。
        - 如果未发现摘要页，则回退到前 3 页文本。

        Args:
            file_path: 目标 PDF 路径。

        Returns:
            tuple[str, int]: `(提取文本, PDF 总页数)`。
        """
        abstract_pattern = re.compile(r"\b(?:abstract|a\s*b\s*s\s*t\s*r\s*a\s*c\s*t)\b|摘要", re.I)
        max_pages_if_not_found = 3

        chunks: list[str] = []
        found_abstract = False

        with fitz.open(str(file_path)) as document:
            page_count = len(document)
            for index, page in enumerate(document):
                text = page.get_text("text") or ""
                chunks.append(text)

                if abstract_pattern.search(text):
                    found_abstract = True
                    break

                if index + 1 >= max_pages_if_not_found:
                    break

        text = "\n".join(chunks if found_abstract else chunks[:max_pages_if_not_found]).strip()
        return text, page_count
