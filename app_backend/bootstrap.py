from __future__ import annotations

import config_data as config
from app_backend.db.connection import DatabaseManager
from app_backend.repositories.config_repository import ConfigRepository
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.memory_repository import MemoryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.repositories.sync_repository import SyncRepository
from app_backend.services.document_ingest_service import DocumentIngestService
from app_backend.services.chat_service import ChatService
from app_backend.services.library_sync_service import LibrarySyncService
from app_backend.services.memory_service import MemoryService
from app_backend.services.metadata_extractor import MetadataExtractorService
from app_backend.services.pdf_parser import PDFParserService
from app_backend.services.retriever_service import RetrieverService
from app_backend.services.vector_index_service import VectorIndexService


class ServiceContainer:
    """简单的依赖容器。

    统一管理数据库、仓储层和服务层实例，方便 API、脚本和后续 agent 模块复用。
    """

    def __init__(self) -> None:
        """构建整套后端服务实例。"""
        config.ensure_runtime_directories()
        self.db_manager = DatabaseManager()

        self.config_repository = ConfigRepository(self.db_manager)
        self.document_repository = DocumentRepository(self.db_manager)
        self.sync_repository = SyncRepository(self.db_manager)
        self.session_repository = SessionRepository(self.db_manager)
        self.memory_repository = MemoryRepository(self.db_manager)

        self.pdf_parser = PDFParserService()
        self.metadata_extractor = MetadataExtractorService()
        self.vector_index_service = VectorIndexService()

        self.document_ingest_service = DocumentIngestService(
            document_repository=self.document_repository,
            pdf_parser=self.pdf_parser,
            metadata_extractor=self.metadata_extractor,
            vector_index_service=self.vector_index_service,
        )
        self.library_sync_service = LibrarySyncService(
            ingest_service=self.document_ingest_service,
            sync_repository=self.sync_repository,
            config_repository=self.config_repository,
        )
        self.memory_service = MemoryService(self.memory_repository)
        self.retriever_service = RetrieverService(
            document_repository=self.document_repository,
            vector_index_service=self.vector_index_service,
        )
        self.chat_service = ChatService(
            session_repository=self.session_repository,
            memory_service=self.memory_service,
            retriever_service=self.retriever_service,
        )
