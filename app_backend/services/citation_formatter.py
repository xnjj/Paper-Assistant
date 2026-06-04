from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Any


_CONFERENCE_HINT_PATTERN = re.compile(
    r"(conference|proceedings|symposium|workshop|meeting|icml|neurips|aaai|ijcai|acl|emnlp|cvpr|iccv|eccv|会议|大会|研讨会)",
    re.IGNORECASE,
)
_JOURNAL_HINT_PATTERN = re.compile(
    r"(journal|transactions|letters|magazine|review|学报|期刊|杂志)",
    re.IGNORECASE,
)
_ONLINE_HINT_PATTERN = re.compile(r"(arxiv|preprint|online|web|网页|预印本|网络首发)", re.IGNORECASE)
_PLACEHOLDER_DOI_PATTERN = re.compile(r"(?:^|[./_-])x{2,}(?:$|[./_-])", re.IGNORECASE)


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
    publisher: str = "",
    publisher_place: str = "",
    volume: str = "",
    issue: str = "",
    pages: str = "",
    publication_date: str = "",
    article_number: str = "",
    degree_institution: str = "",
    degree_location: str = "",
    proceedings_title: str = "",
    conference_name: str = "",
    access_date: str = "",
) -> str:
    """根据可用元数据生成近似 GB/T 7714-2015 的参考文献文本。

    这里不是完整 CSL 引擎，而是项目内的轻量格式化器：优先保证字段顺序、
    文献类型标识、卷期页码、DOI/URL 和电子资源引用日期尽量规范。
    """
    author_text = _format_authors(authors)
    clean_title = _clean_text(title)
    clean_publication_date = _clean_date(publication_date) or _clean_date(year)
    clean_year = _clean_year(clean_publication_date or year)
    clean_venue = _clean_text(venue)
    clean_doi = _clean_doi(doi)
    clean_url = _clean_url(url)
    clean_publisher = _clean_text(publisher)
    clean_publisher_place = _clean_text(publisher_place)
    clean_volume = _clean_text(volume)
    clean_issue = _clean_text(issue)
    clean_pages = _clean_pages(pages)
    clean_article_number = _clean_text(article_number)
    clean_degree_institution = _clean_text(degree_institution)
    clean_degree_location = _clean_text(degree_location)
    clean_proceedings_title = _clean_text(proceedings_title)
    clean_conference_name = _clean_text(conference_name)
    clean_access_date = _clean_access_date(access_date)
    type_mark = _resolve_type_mark(
        document_type=document_type,
        source_type=source_type,
        venue=clean_venue,
        url=clean_url,
    )

    publication_part = _format_publication_part(
        venue=clean_venue,
        year=clean_year,
        publication_date=clean_publication_date,
        publisher=clean_publisher,
        publisher_place=clean_publisher_place,
        volume=clean_volume,
        issue=clean_issue,
        pages=clean_pages,
        article_number=clean_article_number,
        degree_institution=clean_degree_institution,
        degree_location=clean_degree_location,
        proceedings_title=clean_proceedings_title,
        conference_name=clean_conference_name,
        type_mark=type_mark,
    )

    parts: list[str] = []
    if author_text:
        parts.append(f"{author_text}.")
    if clean_title:
        if publication_part.startswith("//"):
            parts.append(f"{clean_title}{type_mark}{publication_part}")
            publication_part = ""
        else:
            parts.append(f"{clean_title}{type_mark}.")
    if publication_part:
        parts.append(publication_part)
    if _is_online_type(type_mark) and (clean_url or clean_doi):
        parts.append(f"[{clean_access_date or date.today().isoformat()}].")
    if clean_doi:
        parts.append(f"DOI: {clean_doi}.")
    if clean_url and clean_url.lower() != f"https://doi.org/{clean_doi}".lower():
        parts.append(f"{clean_url}.")

    citation = " ".join(parts).strip()
    return _normalize_punctuation(citation)


def _format_publication_part(
    *,
    venue: str,
    year: str,
    publication_date: str,
    publisher: str,
    publisher_place: str,
    volume: str,
    issue: str,
    pages: str,
    article_number: str,
    degree_institution: str,
    degree_location: str,
    proceedings_title: str,
    conference_name: str,
    type_mark: str,
) -> str:
    """按文献类型拼接出版项，尽量贴近 GB/T 的常见字段顺序。"""
    type_code = type_mark.strip("[]").upper()
    date_text = publication_date or year
    page_text = pages or article_number

    if type_code in {"J", "J/OL"}:
        return _format_journal_part(
            venue=venue,
            date_text=date_text,
            volume=volume,
            issue=issue,
            page_text=page_text,
        )

    if type_code in {"C", "C/OL"}:
        proceedings = proceedings_title or conference_name or venue
        base = f"//{proceedings}" if proceedings else ""
        place_publisher = _format_place_publisher(
            place=publisher_place,
            publisher=publisher,
            year=date_text,
        )
        if place_publisher:
            base = f"{base}. {place_publisher}" if base else place_publisher
        if page_text:
            base = f"{base}: {page_text}" if base else page_text
        return f"{base}." if base else ""

    if type_code == "D":
        place_publisher = _format_place_publisher(
            place=degree_location or publisher_place,
            publisher=degree_institution or publisher or venue,
            year=date_text,
        )
        return f"{place_publisher}." if place_publisher else ""

    if type_code in {"M", "R", "S", "P"}:
        place_publisher = _format_place_publisher(
            place=publisher_place,
            publisher=publisher or venue,
            year=date_text,
        )
        if page_text:
            place_publisher = f"{place_publisher}: {page_text}" if place_publisher else page_text
        return f"{place_publisher}." if place_publisher else ""

    if type_code in {"EB/OL", "DB/OL"}:
        base = venue or publisher
        if date_text:
            base = f"{base}, {date_text}" if base else date_text
        return f"{base}." if base else ""

    return _format_journal_part(
        venue=venue,
        date_text=date_text,
        volume=volume,
        issue=issue,
        page_text=page_text,
    )


def _format_journal_part(*, venue: str, date_text: str, volume: str, issue: str, page_text: str) -> str:
    """拼接期刊类出版项：刊名, 年, 卷(期): 页码/文章号。"""
    base = venue
    if date_text:
        base = f"{base}, {date_text}" if base else date_text

    volume_issue = _format_volume_issue(volume=volume, issue=issue)
    if volume_issue:
        base = f"{base}, {volume_issue}" if base else volume_issue
    if page_text:
        base = f"{base}: {page_text}" if base else page_text
    return f"{base}." if base else ""


def _format_place_publisher(*, place: str, publisher: str, year: str) -> str:
    """拼接出版地、出版者和年份。"""
    if place and publisher:
        base = f"{place}: {publisher}"
    else:
        base = publisher or place
    if year:
        base = f"{base}, {year}" if base else year
    return base


def _format_volume_issue(*, volume: str, issue: str) -> str:
    """把卷号和期号拼接为 GB/T 常见的 卷(期) 形式。"""
    if volume and issue:
        return f"{volume}({issue})"
    return volume or (f"({issue})" if issue else "")


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
    """根据显式类型、来源和出版信息推断 GB/T 文献类型标识。"""
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
    """规范化调用方传入的文献类型。"""
    if not document_type:
        return ""
    raw_type = document_type.strip().lower().strip("[]")
    type_aliases = {
        "journal-article": "J",
        "journal article": "J",
        "journal": "J",
        "article": "J",
        "j": "J",
        "j/ol": "J/OL",
        "journal/online": "J/OL",
        "proceedings-article": "C",
        "proceedings-series": "C",
        "conference-paper": "C",
        "conference": "C",
        "c": "C",
        "c/ol": "C/OL",
        "dissertation": "D",
        "thesis": "D",
        "degree thesis": "D",
        "d": "D",
        "book": "M",
        "book-chapter": "M",
        "book-section": "M",
        "monograph": "M",
        "m": "M",
        "report": "R",
        "r": "R",
        "standard": "S",
        "patent": "P",
        "posted-content": "EB/OL",
        "preprint": "EB/OL",
        "online": "EB/OL",
        "web": "EB/OL",
        "eb/ol": "EB/OL",
        "ebol": "EB/OL",
        "db/ol": "DB/OL",
    }
    normalized = type_aliases.get(raw_type, document_type.strip().upper().strip("[]"))
    if not normalized:
        return ""
    if normalized in {"J", "J/OL", "C", "C/OL", "M", "D", "R", "N", "P", "S", "Z", "DB/OL", "EB/OL"}:
        return f"[{normalized}]"
    return f"[{normalized}]"


def _is_online_type(type_mark: str) -> bool:
    """判断文献类型是否需要附带引用日期。"""
    return "/OL" in type_mark.upper()


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


def _clean_date(value: Any) -> str:
    """规范化日期字段，支持 YYYY、YYYY-MM、YYYY-MM-DD 三种粒度。"""
    text = _clean_text(value)
    if not text:
        return ""
    match = re.search(r"\b(19\d{2}|20\d{2})(?:[-/.年](\d{1,2})(?:[-/.月](\d{1,2}))?)?", text)
    if not match:
        return ""
    year = match.group(1)
    month = match.group(2)
    day = match.group(3)
    if month and day:
        return f"{year}-{int(month):02d}-{int(day):02d}"
    if month:
        return f"{year}-{int(month):02d}"
    return year


def _clean_doi(value: Any) -> str:
    """规范化 DOI 字段，并过滤明显的占位 DOI。"""
    text = _clean_text(value)
    if not text:
        return ""
    text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
    if "doi.org/" in text.lower():
        text = text.split("doi.org/", 1)[1]
    text = text.rstrip(".,;")
    if _PLACEHOLDER_DOI_PATTERN.search(text):
        return ""
    return text


def _clean_url(value: Any) -> str:
    """规范化 URL 字段，缺失时返回空字符串。"""
    return _clean_text(value).rstrip(".,;")


def _clean_pages(value: Any) -> str:
    """规范化页码字段，统一常见连接符。"""
    cleaned = _clean_text(value)
    cleaned = cleaned.replace("--", "-").replace("–", "-").replace("—", "-")
    return cleaned.strip(" :.,;")


def _clean_access_date(value: Any) -> str:
    """规范化电子资源引用日期，优先保留 YYYY-MM-DD / YYYY-MM / YYYY 形式。"""
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    match = re.search(r"\b(19\d{2}|20\d{2})(?:[-/](\d{1,2})(?:[-/](\d{1,2}))?)?\b", cleaned)
    if not match:
        return cleaned
    year = match.group(1)
    month = match.group(2)
    day = match.group(3)
    if month and day:
        return f"{year}-{int(month):02d}-{int(day):02d}"
    if month:
        return f"{year}-{int(month):02d}"
    return year


def _normalize_punctuation(citation: str) -> str:
    """压缩多余空白并整理末尾标点。"""
    normalized = re.sub(r"\s+", " ", citation).strip()
    normalized = re.sub(r"\s+([,.;:])", r"\1", normalized)
    normalized = re.sub(r"\.{2,}", ".", normalized)
    normalized = re.sub(r"\.\s*(//)", r"\1", normalized)
    normalized = normalized.rstrip(" ")
    return normalized
