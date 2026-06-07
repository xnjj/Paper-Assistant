from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz

from app_backend.models import ParsedDocument


_ABSTRACT_PATTERN = re.compile(
    r"\b(?:abstract|a\s*b\s*s\s*t\s*r\s*a\s*c\s*t)\b|摘要",
    re.IGNORECASE,
)


class PDFParserService:
    """Parse PDF files into full-text and metadata-friendly text views.

    The parser now serves two downstream needs at once:
    - `raw_text`: full extracted text for storage and vector indexing
    - `abstract_priority_text`: a shorter text window that prioritizes the
      title/abstract area for metadata extraction
    """

    def parse(self, file_path: str) -> ParsedDocument:
        """Parse one PDF file into a normalized document object.

        Args:
            file_path: Absolute or relative path to a local PDF file.

        Returns:
            ParsedDocument: Parsed output used by metadata extraction and
            indexing layers.
        """
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File does not exist: {path}")

        file_hash = self._compute_file_hash(path)
        page_texts = self._extract_all_page_texts(path)
        full_text = self._join_page_texts(page_texts)

        if not full_text:
            raise ValueError("PDF text is empty. The file may be scanned or protected.")

        abstract_priority_text = self._build_abstract_priority_text(page_texts, full_text)

        return ParsedDocument(
            file_path=str(path),
            file_name=path.name,
            file_hash=file_hash,
            raw_text=full_text,
            page_count=len(page_texts),
            abstract_priority_text=abstract_priority_text,
            page_texts=page_texts,
        )

    def compute_file_hash(self, file_path: str | Path) -> str:
        """Compute the SHA256 hash of one local PDF file without full parsing."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File does not exist: {path}")
        return self._compute_file_hash(path)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute a SHA256 hash for file content."""
        digest = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _extract_all_page_texts(self, file_path: Path) -> list[str]:
        """Extract normalized text from every page in one PDF."""
        page_texts: list[str] = []
        with fitz.open(str(file_path)) as document:
            for page in document:
                page_texts.append(self._normalize_text(page.get_text("text") or ""))
        return page_texts

    def _join_page_texts(self, page_texts: list[str]) -> str:
        """Join page texts into one full-text string."""
        return "\n\n".join(text for text in page_texts if text).strip()

    def _build_abstract_priority_text(self, page_texts: list[str], full_text: str) -> str:
        """Build a shorter text view that prioritizes title/abstract pages.

        Strategy:
        - always keep the first one or two pages for title/header signals
        - if an abstract page is detected, include that page plus its neighbors
        - fall back to the beginning of the full text when no abstract is found
        """
        if not page_texts:
            return full_text[:18000]

        candidate_indexes: list[int] = []
        leading_page_count = min(2, len(page_texts))
        candidate_indexes.extend(range(leading_page_count))

        abstract_index = self._find_abstract_page_index(page_texts)
        if abstract_index is not None:
            for index in range(max(0, abstract_index - 1), min(len(page_texts), abstract_index + 2)):
                candidate_indexes.append(index)

        ordered_unique_indexes: list[int] = []
        seen_indexes: set[int] = set()
        for index in candidate_indexes:
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            ordered_unique_indexes.append(index)

        focused_chunks = [page_texts[index] for index in ordered_unique_indexes if page_texts[index]]
        focused_text = "\n\n".join(focused_chunks).strip()

        if not focused_text:
            focused_text = full_text

        return focused_text[:18000]

    def _find_abstract_page_index(self, page_texts: list[str]) -> int | None:
        """Return the first page index that appears to contain an abstract."""
        for index, text in enumerate(page_texts):
            if _ABSTRACT_PATTERN.search(text):
                return index
        return None

    def _normalize_text(self, text: str) -> str:
        """Normalize page text while preserving paragraph boundaries."""
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
        normalized_lines: list[str] = []
        blank_pending = False

        for line in lines:
            if not line:
                if normalized_lines:
                    blank_pending = True
                continue

            if blank_pending:
                normalized_lines.append("")
                blank_pending = False
            normalized_lines.append(line)

        return "\n".join(normalized_lines).strip()
