from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


_CONFERENCE_HINT_PATTERN = re.compile(
    r"(conference|proceedings|symposium|workshop|meeting|icml|neurips|aaai|ijcai|acl|emnlp|cvpr|iccv|eccv|会议|大会|研讨会)",
    re.IGNORECASE,
)
_JOURNAL_HINT_PATTERN = re.compile(
    r"(journal|transactions|letters|magazine|review|学报|期刊|杂志)",
    re.IGNORECASE,
)
_ONLINE_HINT_PATTERN = re.compile(r"(arxiv|preprint|online|web|网页|预印本)", re.IGNORECASE)


def format_gbt7714_citation(
    *,
    authors: Iterable[Any] | str | None = None,
    title: str = "",
    year: str = "",
    venue: str = "",
    doi: str = "",
    url: str = "",
    source_type: str = "",
    document_type: str | None = None,
) -> str:
    """根据可用元数据生成近似 GB/T 7714-2015 的参考文献文本。"""
    author_text = _format_authors(authors)
    clean_title = _clean_text(title)
    clean_year = _clean_year(year)
    clean_venue = _clean_text(venue)
    clean_doi = _clean_doi(doi)
    clean_url = _clean_url(url)
    type_mark = _resolve_type_mark(
        document_type=document_type,
        source_type=source_type,
        venue=clean_venue,
        url=clean_url,
    )

    parts: list[str] = []
    if author_text:
        parts.append(f"{author_text}.")
    if clean_title:
        parts.append(f"{clean_title}{type_mark}.")
    if clean_venue and clean_year:
        parts.append(f"{clean_venue}, {clean_year}.")
    elif clean_venue:
        parts.append(f"{clean_venue}.")
    elif clean_year:
        parts.append(f"{clean_year}.")
    if clean_doi:
        parts.append(f"DOI: {clean_doi}.")
    if clean_url and clean_url.lower() != f"https://doi.org/{clean_doi}".lower():
        parts.append(f"{clean_url}.")

    citation = " ".join(parts).strip()
    return _normalize_punctuation(citation)


def _format_authors(authors: Iterable[Any] | str | None) -> str:
    """清洗作者列表并保留全部作者，不做数量截断。"""
    if authors is None:
        return ""
    if isinstance(authors, str):
        raw_authors = re.split(r"\s*(?:,|，|、|;|；|\band\b)\s*", authors)
    else:
        raw_authors = [str(author) for author in authors]

    cleaned_authors: list[str] = []
    seen: set[str] = set()
    for author in raw_authors:
        cleaned = _clean_text(author).strip(" ,;，；、")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_authors.append(cleaned)
    return ", ".join(cleaned_authors)


def _resolve_type_mark(
    *,
    document_type: str | None,
    source_type: str,
    venue: str,
    url: str,
) -> str:
    """根据来源和出版信息推断 GB/T 文献类型标识。"""
    explicit_type = _normalize_document_type(document_type)
    if explicit_type:
        return explicit_type

    lowered_source = source_type.strip().lower()
    if lowered_source in {"external", "web", "online", "arxiv"}:
        return "[EB/OL]"
    if _ONLINE_HINT_PATTERN.search(venue):
        return "[EB/OL]"
    if _CONFERENCE_HINT_PATTERN.search(venue):
        return "[C]"
    if _JOURNAL_HINT_PATTERN.search(venue):
        return "[J]"
    if venue:
        return "[J]"
    if url:
        return "[EB/OL]"
    return ""


def _normalize_document_type(document_type: str | None) -> str:
    """规范化调用方显式传入的文献类型。"""
    if not document_type:
        return ""
    normalized = document_type.strip().upper().strip("[]")
    if not normalized:
        return ""
    if normalized in {"J", "C", "M", "D", "R", "N", "P", "S", "Z"}:
        return f"[{normalized}]"
    if normalized in {"EB/OL", "EBOL", "ONLINE"}:
        return "[EB/OL]"
    return f"[{normalized}]"


def _clean_text(value: Any) -> str:
    """清理任意文本字段中的空白和尾部标点。"""
    if value is None:
        return ""
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned.rstrip(" .。")


def _clean_year(value: Any) -> str:
    """从年份字段中提取四位年份，缺失时返回空字符串。"""
    text = _clean_text(value)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    return match.group(1) if match else text


def _clean_doi(value: Any) -> str:
    """规范化 DOI 字段，缺失时返回空字符串。"""
    text = _clean_text(value)
    if not text:
        return ""
    if "doi.org/" in text.lower():
        text = text.split("doi.org/", 1)[1]
    return text.rstrip(".,;")


def _clean_url(value: Any) -> str:
    """规范化 URL 字段，缺失时返回空字符串。"""
    return _clean_text(value).rstrip(".,;")


def _normalize_punctuation(citation: str) -> str:
    """压缩多余空白并整理末尾标点。"""
    normalized = re.sub(r"\s+", " ", citation).strip()
    normalized = re.sub(r"\.{2,}", ".", normalized)
    return normalized
