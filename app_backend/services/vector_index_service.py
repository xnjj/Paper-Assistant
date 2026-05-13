from __future__ import annotations

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

import config_data as config


_SENTENCE_ENDINGS = frozenset("。！？.!?；;")


class VectorIndexService:
    """Vector index service.

    Responsible for:
    - splitting text into chunks
    - generating embeddings
    - writing chunks to Chroma
    """

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 150) -> None:
        """Initialize vector index service.

        Args:
            chunk_size: Maximum character length of a chunk.
            chunk_overlap: Character overlap between adjacent chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = "text-embedding-v4"
        self.vector_store = Chroma(
            collection_name=config.DATABASE_TABLE,
            embedding_function=DashScopeEmbeddings(model=self.embedding_model),
            persist_directory=config.DATABASE_FILE,
        )

    def _split_long_text(self, text: str) -> list[str]:
        """按固定窗口切分超长文本。

        Args:
            text: 超过 chunk_size 的长文本，通常是没有明显句子边界的内容。

        Returns:
            list[str]: 按 chunk_size 和 chunk_overlap 切分后的文本片段。
        """
        chunks: list[str] = []
        step = max(1, self.chunk_size - self.chunk_overlap)

        for start in range(0, len(text), step):
            chunk = text[start:start + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)

        return chunks

    def _split_paragraph(self, paragraph: str) -> list[str]:
        """将单个段落切分为句子级语义单元。

        Args:
            paragraph: 已去除首尾空白的段落文本。

        Returns:
            list[str]: 优先按句末标点切分的文本单元；超长句子会继续按固定窗口切分。
        """
        if len(paragraph) <= self.chunk_size:
            return [paragraph]

        units: list[str] = []
        start = 0
        for index, char in enumerate(paragraph):
            if char in _SENTENCE_ENDINGS:
                sentence = paragraph[start:index + 1].strip()
                if sentence:
                    units.extend(
                        [sentence]
                        if len(sentence) <= self.chunk_size
                        else self._split_long_text(sentence)
                    )
                start = index + 1

        tail = paragraph[start:].strip()
        if tail:
            units.extend(
                [tail] if len(tail) <= self.chunk_size else self._split_long_text(tail)
            )

        return units

    def _semantic_units(self, text: str) -> list[str]:
        """从原始文本中提取段落/句子级语义单元。

        Args:
            text: 待切分的完整正文文本。

        Returns:
            list[str]: 按空行识别段落，并对超长段落进一步切句后的语义单元列表。
        """
        paragraphs: list[str] = []
        paragraph_lines: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                paragraph_lines.append(stripped)
            elif paragraph_lines:
                paragraphs.append("\n".join(paragraph_lines))
                paragraph_lines.clear()

        if paragraph_lines:
            paragraphs.append("\n".join(paragraph_lines))

        units: list[str] = []
        for paragraph in paragraphs:
            units.extend(self._split_paragraph(paragraph))

        return units

    def split_text(self, text: str) -> list[str]:
        """按段落/句子切分文本，并在必要时使用固定窗口兜底。

        Args:
            text: 待切分的完整正文文本。

        Returns:
            list[str]: 不超过 chunk_size 为主、相邻片段保留 chunk_overlap 的文本片段。
        """
        if not text.strip():
            return []

        chunks: list[str] = []
        current = ""

        for unit in self._semantic_units(text):
            separator = "\n\n" if current and "\n" in unit else ""
            next_chunk = f"{current}{separator}{unit}" if current else unit

            if len(next_chunk) <= self.chunk_size:
                current = next_chunk
                continue

            if current:
                chunks.append(current)
                current = (
                    current[-self.chunk_overlap:].strip()
                    if self.chunk_overlap > 0
                    else ""
                )

            separator = "\n\n" if current and "\n" in unit else ""
            next_chunk = f"{current}{separator}{unit}" if current else unit
            if len(next_chunk) <= self.chunk_size:
                current = next_chunk
            else:
                if current:
                    chunks.append(current)
                chunks.extend(self._split_long_text(unit))
                current = ""

        if current:
            chunks.append(current)

        return chunks

    def index_document(self, document_id: int, text: str) -> list[dict]:
        """Create chunks for one document and write them into the vector store.

        Args:
            document_id: Primary key of the document in the structured database.
            text: Document body to index.

        Returns:
            Structured metadata for each indexed chunk.
        """
        chunks = self.split_text(text)
        indexed_chunks: list[dict] = []

        for index, chunk_text in enumerate(chunks):
            vector_id = f"doc-{document_id}-chunk-{index}"
            self.vector_store.add_texts(
                texts=[chunk_text],
                metadatas=[{"document_id": document_id, "chunk_index": index}],
                ids=[vector_id],
            )
            indexed_chunks.append(
                {
                    "chunk_index": index,
                    "chunk_text": chunk_text,
                    "token_count": len(chunk_text),
                    "vector_id": vector_id,
                    "embedding_model": self.embedding_model,
                }
            )

        return indexed_chunks
