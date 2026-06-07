from __future__ import annotations

import json

import config_data as config
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.services.rerank_service import RerankService
from app_backend.services.vector_index_service import VectorIndexService


class RetrieverService:
    """Library-aware retrieval service.

    This service combines vector recall results with structured document
    metadata so downstream chat prompts can cite titles, abstracts, and files.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        library_repository: LibraryRepository,
        vector_index_service: VectorIndexService,
        rerank_service: RerankService,
    ) -> None:
        """Initialize the retrieval service.

        Args:
            document_repository: Structured document repository used for
                metadata lookups.
            library_repository: Repository used to resolve library collections.
            vector_index_service: Vector search service.
            rerank_service: Candidate reranker used after vector recall.
        """
        self.document_repository = document_repository
        self.library_repository = library_repository
        self.vector_index_service = vector_index_service
        self.rerank_service = rerank_service

    def search(self, query: str, library_id: int, top_k: int = 5, recall_k: int | None = None) -> list[dict]:
        """Search the target library and return reranked chunk-level evidence."""
        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

        effective_recall_k = max(recall_k or max(top_k * 4, 20), top_k)
        vector_results = self.vector_index_service.search(
            collection_name=library.collection_name,
            library_id=library.id,
            query=query,
            top_k=effective_recall_k,
        )
        merged_results: list[dict] = []

        for recall_rank, item in enumerate(vector_results):
            metadata = item.metadata or {}
            document_id = metadata.get("document_id")
            if document_id is None:
                continue

            document = self.document_repository.get_by_id(int(document_id))
            if document is None or document.library_id != library_id:
                continue

            authors = self._loads_json_list(document.authors_json)
            merged_results.append(
                {
                    "library_id": library_id,
                    "document_id": document.id,
                    "title": document.title,
                    "authors": authors,
                    "year": document.year,
                    "venue": document.venue,
                    "abstract": document.abstract,
                    "doi": document.doi,
                    "url": document.url,
                    "citation_text_default": document.citation_text_default,
                    "publisher": document.publisher,
                    "publisher_place": document.publisher_place,
                    "volume": document.volume,
                    "issue": document.issue,
                    "pages": document.pages,
                    "article_number": document.article_number,
                    "degree_institution": document.degree_institution,
                    "degree_location": document.degree_location,
                    "proceedings_title": document.proceedings_title,
                    "conference_name": document.conference_name,
                    "publication_date": document.publication_date,
                    "document_type": document.document_type,
                    "file_path": document.file_path,
                    "chunk_index": metadata.get("chunk_index"),
                    "section_type": metadata.get("section_type") or "",
                    "section_title": metadata.get("section_title") or "",
                    "section_chunk_index": metadata.get("section_chunk_index"),
                    "indexable": metadata.get("indexable", True),
                    "chunk_text": item.page_content,
                    "recall_rank": recall_rank,
                }
            )

        return self.rerank_service.rerank(
            query=query,
            candidates=merged_results,
            top_k=top_k,
            max_chunks_per_document=config.CHUNK_LIMIT_PER_PAPER,
        )

    def _loads_json_list(self, raw_value: str) -> list[str]:
        """Decode one JSON list column into a list of strings."""
        try:
            payload = json.loads(raw_value)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [str(item) for item in payload if str(item).strip()]
