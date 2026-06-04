from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app_backend.models import (
    DocumentRecord,
    ExtractedMetadata,
    IngestResult,
    LibraryRecord,
    ParsedDocument,
)
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.services.metadata_extractor import MetadataExtractorService
from app_backend.services.pdf_parser import PDFParserService
from app_backend.services.vector_index_service import VectorIndexService


@dataclass
class PreparedIngestPayload:
    """保存已完成 PDF 解析和元数据抽取、但尚未写入数据库的入库载荷。"""

    parsed_document: ParsedDocument
    metadata: ExtractedMetadata
    source_type: str


class DocumentIngestService:
    """Document ingest orchestrator.

    This service coordinates:
    PDF parsing -> metadata extraction -> structured persistence ->
    chunking and vector indexing.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        library_repository: LibraryRepository,
        pdf_parser: PDFParserService,
        metadata_extractor: MetadataExtractorService,
        vector_index_service: VectorIndexService,
    ) -> None:
        """Initialize the ingest service.

        Args:
            document_repository: Structured document repository.
            library_repository: Library repository used to resolve the target library.
            pdf_parser: PDF parser service.
            metadata_extractor: Metadata extraction service.
            vector_index_service: Vector chunking and indexing service.
        """
        self.document_repository = document_repository
        self.library_repository = library_repository
        self.pdf_parser = pdf_parser
        self.metadata_extractor = metadata_extractor
        self.vector_index_service = vector_index_service

    def ingest_paths(
        self,
        pdf_paths: list[str],
        source_type: str = "local_folder",
        library_id: int | None = None,
    ) -> list[IngestResult]:
        """Batch ingest a list of PDF files into one library.

        Args:
            pdf_paths: File paths to ingest.
            source_type: Document source label such as `upload` or `local_folder`.
            library_id: Explicit target library id.
        """
        library = self._resolve_library(library_id)
        return [
            self._ingest_one_path(
                path=path,
                source_type=source_type,
                library=library,
            )
            for path in pdf_paths
        ]

    def ingest_path(
        self,
        pdf_path: str,
        source_type: str = "local_folder",
        library_id: int | None = None,
    ) -> IngestResult:
        """Ingest one PDF file into one library."""
        library = self._resolve_library(library_id)
        return self._ingest_one_path(
            path=pdf_path,
            source_type=source_type,
            library=library,
        )

    def compute_file_hash(self, pdf_path: str) -> str:
        """Compute the content hash of one PDF file without full parsing."""
        return self.pdf_parser.compute_file_hash(pdf_path)

    def document_needs_repair(self, document: DocumentRecord) -> bool:
        """判断已有文献是否需要重建结构化 chunk 和向量索引。"""
        return self._document_needs_repair(document)

    def prepare_ingest_payload(
        self,
        pdf_path: str,
        source_type: str = "local_folder",
    ) -> PreparedIngestPayload:
        """解析 PDF 并抽取元数据，但不写入数据库或向量库。

        该方法用于同步线程池中的并发准备阶段；真正的数据库写入和
        Chroma 写入仍由同步主线程调用 `persist_prepared_payload()` 完成。
        """
        parsed_document = self.pdf_parser.parse(pdf_path)
        metadata = self.metadata_extractor.extract(parsed_document)
        return PreparedIngestPayload(
            parsed_document=parsed_document,
            metadata=metadata,
            source_type=source_type,
        )

    def persist_prepared_payload(
        self,
        *,
        prepared_payload: PreparedIngestPayload,
        library: LibraryRecord,
    ) -> IngestResult:
        """把已准备好的文献载荷写入数据库和向量库。

        该方法必须由同步主线程调用，避免多个 LLM worker 同时写入
        SQLite 或 Chroma 持久化目录。
        """
        parsed_document = prepared_payload.parsed_document
        metadata = prepared_payload.metadata
        document_id: int | None = None
        try:
            existing_document = self.document_repository.get_by_file_hash(
                library.id,
                parsed_document.file_hash,
            )
            if existing_document is not None:
                if self._document_needs_repair(existing_document):
                    document_id = existing_document.id
                    self._repair_incomplete_document(
                        library=library,
                        document=existing_document,
                        parsed_document=parsed_document,
                    )
                    return IngestResult(
                        path=parsed_document.file_path,
                        success=True,
                        status="saved",
                        library_id=library.id,
                        title=existing_document.title,
                        file_hash=parsed_document.file_hash,
                        document_id=existing_document.id,
                    )

                return IngestResult(
                    path=parsed_document.file_path,
                    success=True,
                    status="duplicate",
                    library_id=library.id,
                    title=existing_document.title,
                    file_hash=parsed_document.file_hash,
                    document_id=existing_document.id,
                    error="The same file content is already stored in this library.",
                )

            document_id = self._create_and_index_document(
                library=library,
                parsed_document=parsed_document,
                metadata=metadata,
                source_type=prepared_payload.source_type,
            )
            return IngestResult(
                path=parsed_document.file_path,
                success=True,
                status="saved",
                library_id=library.id,
                title=metadata.title,
                file_hash=parsed_document.file_hash,
                document_id=document_id,
            )
        except Exception as exc:
            if document_id is not None:
                self.document_repository.update_document_index_state(
                    document_id,
                    status="index_failed",
                )
            return IngestResult(
                path=parsed_document.file_path,
                success=False,
                status="failed",
                library_id=library.id,
                file_hash=parsed_document.file_hash,
                document_id=document_id,
                error=str(exc),
            )

    def _resolve_library(self, library_id: int | None) -> LibraryRecord:
        """Resolve the target library for one ingest request."""
        if library_id is None:
            raise ValueError("Please choose a library before ingesting documents.")

        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")
        return library

    def _ingest_one_path(
        self,
        *,
        path: str,
        source_type: str,
        library: LibraryRecord,
    ) -> IngestResult:
        """Ingest one file and return its final ingest result."""
        resolved_path = str(Path(path))
        file_hash = ""
        document_id: int | None = None
        try:
            parsed_document = self.pdf_parser.parse(path)
            resolved_path = parsed_document.file_path
            file_hash = parsed_document.file_hash
            existing_document = self.document_repository.get_by_file_hash(
                library.id,
                parsed_document.file_hash,
            )
            if existing_document is not None:
                if self._document_needs_repair(existing_document):
                    document_id = existing_document.id
                    self._repair_incomplete_document(
                        library=library,
                        document=existing_document,
                        parsed_document=parsed_document,
                    )
                    return IngestResult(
                        path=parsed_document.file_path,
                        success=True,
                        status="saved",
                        library_id=library.id,
                        title=existing_document.title,
                        file_hash=parsed_document.file_hash,
                        document_id=existing_document.id,
                    )

                return IngestResult(
                    path=parsed_document.file_path,
                    success=True,
                    status="duplicate",
                    library_id=library.id,
                    title=existing_document.title,
                    file_hash=parsed_document.file_hash,
                    document_id=existing_document.id,
                    error="The same file content is already stored in this library.",
                )

            metadata = self.metadata_extractor.extract(parsed_document)
            document_id = self._create_and_index_document(
                library=library,
                parsed_document=parsed_document,
                metadata=metadata,
                source_type=source_type,
            )
            return IngestResult(
                path=parsed_document.file_path,
                success=True,
                status="saved",
                library_id=library.id,
                title=metadata.title,
                file_hash=parsed_document.file_hash,
                document_id=document_id,
            )
        except Exception as exc:
            if document_id is not None:
                self.document_repository.update_document_index_state(
                    document_id,
                    status="index_failed",
                )
            return IngestResult(
                path=resolved_path,
                success=False,
                status="failed",
                library_id=library.id,
                file_hash=file_hash,
                document_id=document_id,
                error=str(exc),
            )

    def _create_and_index_document(
        self,
        *,
        library: LibraryRecord,
        parsed_document: ParsedDocument,
        metadata: ExtractedMetadata,
        source_type: str,
    ) -> int:
        """在主线程中创建文献记录、写入向量索引，并更新文献索引状态。"""
        document_id = self.document_repository.create_document(
            library_id=library.id,
            file_hash=parsed_document.file_hash,
            file_path=parsed_document.file_path,
            file_name=parsed_document.file_name,
            title=metadata.title,
            abstract=metadata.abstract,
            authors=metadata.authors,
            keywords=metadata.keywords,
            year=metadata.year,
            doi=metadata.doi,
            url=metadata.url,
            venue=metadata.venue,
            citation_text_default=metadata.citation_text_default,
            source_type=source_type,
            source_uri=parsed_document.file_path,
            content_text=parsed_document.raw_text,
            status="indexing",
            publication_date=metadata.publication_date,
            document_type=metadata.document_type,
            publisher=metadata.publisher,
            publisher_place=metadata.publisher_place,
            volume=metadata.volume,
            issue=metadata.issue,
            pages=metadata.pages,
            article_number=metadata.article_number,
            degree_institution=metadata.degree_institution,
            degree_location=metadata.degree_location,
            proceedings_title=metadata.proceedings_title,
            conference_name=metadata.conference_name,
            extra_metadata=metadata.extra_metadata,
        )
        self._index_document_contents(
            library=library,
            document_id=document_id,
            text=parsed_document.raw_text,
        )
        self.document_repository.update_document_index_state(
            document_id,
            status="indexed",
            content_text=parsed_document.raw_text,
        )
        return document_id

    def _document_needs_repair(self, document: DocumentRecord) -> bool:
        """Return whether one existing document still needs chunk index repair."""
        chunk_count = self.document_repository.count_chunks(document.id)
        return document.status != "indexed" or chunk_count == 0

    def _repair_incomplete_document(
        self,
        *,
        library: LibraryRecord,
        document: DocumentRecord,
        parsed_document: ParsedDocument,
    ) -> None:
        """Repair one previously half-indexed document.

        This path is used when a historical sync created the `documents` row but
        failed before the vector index and `document_chunks` were fully written.
        """
        self.document_repository.update_document_index_state(
            document.id,
            status="indexing",
            content_text=parsed_document.raw_text,
        )
        self.document_repository.delete_chunks(document.id)
        self.vector_index_service.delete_document_vectors(
            library.collection_name,
            library.id,
            document.id,
        )
        self._index_document_contents(
            library=library,
            document_id=document.id,
            text=parsed_document.raw_text,
        )
        self.document_repository.update_document_index_state(
            document.id,
            status="indexed",
            content_text=parsed_document.raw_text,
        )

    def _index_document_contents(
        self,
        *,
        library: LibraryRecord,
        document_id: int,
        text: str,
    ) -> None:
        """Write vector chunks and structured chunk rows for one document."""
        indexed_chunks = self.vector_index_service.index_document(
            library_id=library.id,
            collection_name=library.collection_name,
            document_id=document_id,
            text=text,
        )
        for chunk in indexed_chunks:
            self.document_repository.add_chunk(
                library_id=library.id,
                document_id=document_id,
                **chunk,
            )
