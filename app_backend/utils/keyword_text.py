from __future__ import annotations

import re


_ENGLISH_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+\-./]{1,}")
_CJK_SEGMENT_PATTERN = re.compile(r"[\u4e00-\u9fff]+")

_CHINESE_STOP_WORDS = {
    "一个",
    "一些",
    "以及",
    "中的",
    "为了",
    "关于",
    "分析",
    "研究",
    "领域",
    "应用",
}


def build_keyword_search_text(*parts: object) -> str:
    """构造写入 FTS5 的增强检索文本，额外加入中文 2-4 字 ngram。"""
    raw_text = "\n".join(str(part or "") for part in parts if str(part or "").strip())
    cjk_terms = extract_cjk_ngrams(raw_text, min_n=2, max_n=4)
    if cjk_terms:
        return f"{raw_text}\n{' '.join(cjk_terms)}"
    return raw_text


def build_fts_match_expression(query: str) -> str:
    """把用户问题转换为安全的 FTS5 MATCH 表达式。"""
    terms = extract_query_terms(query)
    if not terms and query.strip():
        terms = [query.strip()]
    return " OR ".join(quote_fts_term(term) for term in terms if term.strip())


def extract_query_terms(query: str) -> list[str]:
    """提取中英文关键词；中文优先用 jieba，未安装时退回 ngram。"""
    terms: list[str] = []
    terms.extend(_ENGLISH_TOKEN_PATTERN.findall(query))

    for segment in _CJK_SEGMENT_PATTERN.findall(query):
        terms.extend(extract_cjk_terms(segment))

    deduped_terms: list[str] = []
    seen_terms: set[str] = set()
    for term in terms:
        normalized = term.strip()
        if not normalized or normalized in seen_terms:
            continue
        seen_terms.add(normalized)
        deduped_terms.append(normalized)
    return deduped_terms[:32]


def extract_cjk_terms(text: str) -> list[str]:
    """提取中文查询词，兼容没有安装 jieba 的运行环境。"""
    try:
        import jieba  # type: ignore
    except Exception:
        return extract_cjk_ngrams(text, min_n=2, max_n=4)

    terms: list[str] = []
    for token in jieba.lcut(text):
        normalized = token.strip()
        if len(normalized) < 2 or normalized in _CHINESE_STOP_WORDS:
            continue
        terms.append(normalized)
    return terms or extract_cjk_ngrams(text, min_n=2, max_n=4)


def extract_cjk_ngrams(text: str, *, min_n: int, max_n: int) -> list[str]:
    """为中文连续文本生成短 ngram，提升关键短语命中率。"""
    terms: list[str] = []
    for segment in _CJK_SEGMENT_PATTERN.findall(text):
        for ngram_size in range(min_n, max_n + 1):
            if len(segment) < ngram_size:
                continue
            for index in range(0, len(segment) - ngram_size + 1):
                term = segment[index : index + ngram_size]
                if term not in _CHINESE_STOP_WORDS:
                    terms.append(term)
    return terms


def quote_fts_term(term: str) -> str:
    """转义 FTS5 phrase，避免引号或符号破坏 MATCH 语法。"""
    escaped = term.replace('"', '""')
    return '"' + escaped + '"'
