from __future__ import annotations

import config_data as config
from app_backend.db.connection import DatabaseManager
from app_backend.repositories.config_repository import ConfigRepository
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.memory_repository import MemoryRepository
from app_backend.repositories.session_repository import SessionRepository
from app_backend.repositories.sync_repository import SyncRepository
from app_backend.services.chat_service import ChatService
from app_backend.services.config_service import ConfigService
from app_backend.services.crossref_metadata_enrichment_service import CrossrefMetadataEnrichmentService
from app_backend.services.document_ingest_service import DocumentIngestService
from app_backend.services.agent_orchestrator_service import AgentOrchestratorService
from app_backend.services.external_search_planner_service import ExternalSearchPlannerService
from app_backend.services.keyword_search_service import KeywordSearchService
from app_backend.services.library_sync_service import LibrarySyncService
from app_backend.services.llm_concurrency_limiter import LLMConcurrencyLimiter
from app_backend.services.memory_service import MemoryService
from app_backend.services.metadata_extractor import MetadataExtractorService
from app_backend.services.mcp_external_search_service import MCPExternalSearchService
from app_backend.services.pdf_parser import PDFParserService
from app_backend.services.qwen_rerank_service import QwenRerankService
from app_backend.services.rerank_service import RerankService
from app_backend.services.retriever_service import RetrieverService
from app_backend.services.semantic_chunk_service import SemanticChunkService
from app_backend.services.stdio_mcp_tool_invoker import StdioMCPToolInvoker
from app_backend.services.vector_index_service import VectorIndexService


class ServiceContainer:
    """Simple dependency container shared by the backend entrypoints."""

    def __init__(self) -> None:
        """Construct the full backend service graph."""
        config.ensure_runtime_directories()
        self.db_manager = DatabaseManager()

        self.config_repository = ConfigRepository(self.db_manager)
        self.library_repository = LibraryRepository(self.db_manager)
        self.document_repository = DocumentRepository(self.db_manager)
        self.sync_repository = SyncRepository(self.db_manager)
        self.session_repository = SessionRepository(self.db_manager)
        self.memory_repository = MemoryRepository(self.db_manager)

        self.config_service = ConfigService(
            config_repository=self.config_repository,
            library_repository=self.library_repository,
        )
        self.pdf_parser = PDFParserService()
        self.llm_concurrency_limiter = LLMConcurrencyLimiter()
        self.metadata_extractor = MetadataExtractorService(
            self.config_service,
            self.llm_concurrency_limiter,
        )
        self.semantic_chunk_service = SemanticChunkService(
            config_service=self.config_service,
            llm_limiter=self.llm_concurrency_limiter,
        )
        self.vector_index_service = VectorIndexService(
            self.config_service,
            self.semantic_chunk_service,
        )
        self.keyword_search_service = KeywordSearchService(self.db_manager)
        self.qwen_rerank_service = QwenRerankService(self.config_service)
        self.rerank_service = RerankService(self.qwen_rerank_service)

        self.document_ingest_service = DocumentIngestService(
            document_repository=self.document_repository,
            library_repository=self.library_repository,
            pdf_parser=self.pdf_parser,
            metadata_extractor=self.metadata_extractor,
            vector_index_service=self.vector_index_service,
        )
        self.library_sync_service = LibrarySyncService(
            ingest_service=self.document_ingest_service,
            sync_repository=self.sync_repository,
            library_repository=self.library_repository,
            document_repository=self.document_repository,
            vector_index_service=self.vector_index_service,
        )
        self.memory_service = MemoryService(self.memory_repository)
        self.retriever_service = RetrieverService(
            document_repository=self.document_repository,
            library_repository=self.library_repository,
            vector_index_service=self.vector_index_service,
            rerank_service=self.rerank_service,
            keyword_search_service=self.keyword_search_service,
        )
        self.mcp_tool_invoker = StdioMCPToolInvoker()
        self.external_search_service = MCPExternalSearchService(self.mcp_tool_invoker)
        self.external_search_planner_service = ExternalSearchPlannerService(self.config_service)
        self.crossref_metadata_enrichment_service = CrossrefMetadataEnrichmentService()
        self.agent_orchestrator_service = AgentOrchestratorService(
            session_repository=self.session_repository,
            library_repository=self.library_repository,
            memory_service=self.memory_service,
            retriever_service=self.retriever_service,
            config_service=self.config_service,
            external_search_service=self.external_search_service,
            external_search_planner_service=self.external_search_planner_service,
        )
        self.chat_service = ChatService(
            session_repository=self.session_repository,
            library_repository=self.library_repository,
            memory_service=self.memory_service,
            retriever_service=self.retriever_service,
            config_service=self.config_service,
            agent_orchestrator_service=self.agent_orchestrator_service,
            crossref_metadata_enrichment_service=self.crossref_metadata_enrichment_service,
        )
