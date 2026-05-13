from __future__ import annotations

from pathlib import Path

from app_backend.models import IngestResult
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.services.metadata_extractor import MetadataExtractorService
from app_backend.services.pdf_parser import PDFParserService
from app_backend.services.vector_index_service import VectorIndexService


class DocumentIngestService:
    """文献入库编排服务。

    该层负责编排完整的入库流程：
    `PDF 解析 -> 元数据抽取 -> 结构化入库 -> 切片与向量索引`
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        pdf_parser: PDFParserService,
        metadata_extractor: MetadataExtractorService,
        vector_index_service: VectorIndexService,
    ) -> None:
        """初始化文献入库编排服务。

        Args:
            document_repository: 文献结构化仓储。
            pdf_parser: PDF 解析服务。
            metadata_extractor: 元数据抽取服务。
            vector_index_service: 向量切片与索引服务。
        """
        self.document_repository = document_repository
        self.pdf_parser = pdf_parser
        self.metadata_extractor = metadata_extractor
        self.vector_index_service = vector_index_service

    def ingest_paths(self, pdf_paths: list[str], source_type: str = "local_folder") -> list[IngestResult]:
        """批量处理一组 PDF 路径。

        Args:
            pdf_paths: 待处理文件路径列表。
            source_type: 文献来源类型，如 `upload`、`local_folder`、`arxiv`。

        Returns:
            list[IngestResult]: 逐文件的处理结果，用于 API 直接返回给前端。
        """
        results: list[IngestResult] = []
        for path in pdf_paths:
            try:
                parsed_document = self.pdf_parser.parse(path)
                existing_document = self.document_repository.get_by_file_hash(parsed_document.file_hash)
                if existing_document is not None:
                    results.append(
                        IngestResult(
                            path=parsed_document.file_path,
                            success=True,
                            status="duplicate",
                            title=existing_document.title,
                            file_hash=parsed_document.file_hash,
                            document_id=existing_document.id,
                            error="相同文件内容已入库。",
                        )
                    )
                    continue

                metadata = self.metadata_extractor.extract(parsed_document)
                document_id = self.document_repository.create_document(
                    file_hash=parsed_document.file_hash,
                    file_path=parsed_document.file_path,
                    file_name=parsed_document.file_name,
                    title=metadata.title,
                    abstract=metadata.abstract,
                    authors=metadata.authors,
                    keywords=metadata.keywords,
                    doi=metadata.doi,
                    source_type=source_type,
                    source_uri=parsed_document.file_path,
                    content_text=parsed_document.raw_text,
                    status="indexed",
                )

                indexed_chunks = self.vector_index_service.index_document(document_id, parsed_document.raw_text)
                for chunk in indexed_chunks:
                    self.document_repository.add_chunk(document_id=document_id, **chunk)

                results.append(
                    IngestResult(
                        path=parsed_document.file_path,
                        success=True,
                        status="saved",
                        title=metadata.title,
                        file_hash=parsed_document.file_hash,
                        document_id=document_id,
                    )
                )
            except Exception as exc:
                results.append(
                    IngestResult(
                        path=str(Path(path)),
                        success=False,
                        status="failed",
                        error=str(exc),
                    )
                )
        return results
