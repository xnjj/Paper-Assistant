from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    """PDF 解析层输出。

    Attributes:
        file_path: 文档的绝对路径。
        file_name: 文档文件名。
        file_hash: 文件内容哈希，用于增量同步和去重。
        raw_text: 提取到的全文或关键页文本。
        page_count: PDF 页数。
    """

    file_path: str
    file_name: str
    file_hash: str
    raw_text: str
    page_count: int
    abstract_priority_text: str = ""


@dataclass
class ExtractedMetadata:
    """元数据抽取层输出。"""

    title: str
    abstract: str
    keywords: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    year: str = ""
    doi: str = ""
    url: str = ""
    venue: str = ""
    citation_text_default: str = ""
    language: str = "zh"
    publication_date: str = ""
    document_type: str = ""
    publisher: str = ""
    publisher_place: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    article_number: str = ""
    degree_institution: str = ""
    degree_location: str = ""
    proceedings_title: str = ""
    conference_name: str = ""
    extra_metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DocumentRecord:
    """结构化数据库中的文献记录。"""

    id: int
    library_id: int
    file_hash: str
    file_path: str
    file_name: str
    title: str
    abstract: str
    authors_json: str
    keywords_json: str
    year: str
    doi: str
    url: str
    venue: str
    citation_text_default: str
    source_type: str
    source_uri: str
    content_text: str
    status: str
    created_at: str
    updated_at: str
    publication_date: str = ""
    document_type: str = ""
    publisher: str = ""
    publisher_place: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    article_number: str = ""
    degree_institution: str = ""
    degree_location: str = ""
    proceedings_title: str = ""
    conference_name: str = ""
    extra_metadata_json: str = "{}"


@dataclass
class DocumentChunkRecord:
    """结构化数据库中的文献切片记录。"""

    id: int
    library_id: int
    document_id: int
    chunk_index: int
    chunk_text: str
    token_count: int
    vector_id: str
    embedding_model: str
    created_at: str


@dataclass
class SyncJobRecord:
    """一次文献库同步任务。"""

    id: int
    library_id: int
    folder_path: str
    job_type: str
    status: str
    scanned_count: int
    new_count: int
    skipped_count: int
    failed_count: int
    error_message: str
    started_at: str
    finished_at: str | None


@dataclass
class MemoryRecord:
    """长期/短期记忆记录。"""

    id: int
    scope: str
    session_id: int | None
    memory_type: str
    content: str
    summary: str
    importance: int
    last_used_at: str | None
    created_at: str


@dataclass
class SessionRecord:
    """会话记录。"""

    id: int
    library_id: int | None
    title: str
    user_goal: str
    is_pinned: bool
    created_at: str
    updated_at: str


@dataclass
class MessageRecord:
    """会话消息记录。"""

    id: int
    session_id: int
    role: str
    content: str
    retrieval_context_json: str
    created_at: str


@dataclass
class IngestResult:
    """文档入库流程结果。

    Attributes:
        path: 输入文件路径。
        success: 整体是否成功。
        status: saved / duplicate / failed
        title: 解析出的标题。
        file_hash: 文件哈希。
        document_id: 保存后的文献主键。
        error: 失败或跳过原因。
    """

    path: str
    success: bool
    status: str
    library_id: int | None = None
    title: str = ""
    file_hash: str = ""
    document_id: int | None = None
    error: str = ""


@dataclass
class LibraryRecord:
    """鏂囩尞搴撹褰曘€?"""

    id: int
    name: str
    description: str
    folder_path: str
    collection_name: str
    embedding_model: str
    embedding_max_input_tokens: int
    chunk_mode: str
    created_at: str
    updated_at: str
