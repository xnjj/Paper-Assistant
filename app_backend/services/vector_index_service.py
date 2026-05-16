from __future__ import annotations

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
from app_backend.services.config_service import ConfigService


class VectorIndexService:
    """Vector index service with per-library Chroma collections.

    Responsible for:
    - splitting document text into chunks
    - generating embeddings
    - writing and querying chunks inside the target library collection
    """

    def __init__(self, config_service: ConfigService | None = None, chunk_overlap: int = 150) -> None:
        """Initialize the vector index service.

        Args:
            chunk_overlap: Character overlap between adjacent chunks.
        """
        self.config_service = config_service
        self.default_chunk_size = config.DOCUMENT_CHUNK_MAX_CHARS
        self.base_chunk_overlap = max(0, chunk_overlap)
        self._vector_stores: dict[tuple[str, str, str], Chroma] = {}

    def _get_vector_store(self, collection_name: str, library_id: int | None = None) -> Chroma:
        """Return a cached Chroma instance for one library collection."""
        embedding_model = self._get_embedding_model_name(library_id)
        api_key = self._get_api_key()
        cache_key = (collection_name, embedding_model, api_key)
        if cache_key not in self._vector_stores:
            self._vector_stores[cache_key] = Chroma(
                collection_name=collection_name,
                embedding_function=DashScopeEmbeddings(
                    model=embedding_model,
                    dashscope_api_key=api_key or None,
                ),
                persist_directory=config.DATABASE_FILE,
            )
        return self._vector_stores[cache_key]

    def _get_chunk_size(self, library_id: int | None = None) -> int:
        """Return the effective per-library chunk size.

        The current production splitter still uses character counts as a
        practical proxy for provider token limits, so the configured maximum
        embedding input length is used as the library-level chunk budget.
        """
        if self.config_service is None:
            return max(1, self.default_chunk_size)
        return max(1, self.config_service.get_embedding_max_input_tokens(library_id))

    def _get_chunk_overlap(self, chunk_size: int) -> int:
        """Clamp the overlap so it always stays smaller than the chunk size."""
        return min(self.base_chunk_overlap, max(0, chunk_size - 1))

    def _build_splitter(self, library_id: int | None = None) -> RecursiveCharacterTextSplitter:
        """Build the production chunk splitter.

        The splitter prefers paragraph and sentence boundaries first, then
        falls back to spaces and finally character-level splitting. This keeps
        words and sentences intact whenever the extracted PDF text allows it.
        """
        chunk_mode = "recursive"
        if self.config_service is not None:
            chunk_mode = self.config_service.get_effective_chunk_mode(library_id)
        chunk_size = self._get_chunk_size(library_id)
        chunk_overlap = self._get_chunk_overlap(chunk_size)

        # Semantic chunking is not implemented yet. The config service already
        # falls it back to "recursive", but we still resolve the mode here so
        # indexing/search paths consistently read all library-level index
        # settings by library_id.
        _ = chunk_mode
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            keep_separator=True,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                ". ",
                "! ",
                "? ",
                "; ",
                " ",
                "",
            ],
            length_function=len,
            is_separator_regex=False,
        )

    def split_text(self, text: str, library_id: int | None = None) -> list[str]:
        """Split text with a paragraph-first recursive splitter."""
        if not text.strip():
            return []

        splitter = self._build_splitter(library_id)
        chunks: list[str] = []
        for chunk in splitter.split_text(text):
            cleaned = chunk.strip()
            if cleaned:
                chunks.append(cleaned)
        return chunks

    def _get_embedding_model_name(self, library_id: int | None = None) -> str:
        """Return the active embedding model name."""
        if self.config_service is None:
            return config.EMBEDDING_MODEL_NAME
        return self.config_service.get_embedding_model_name(library_id)

    def _get_api_key(self) -> str:
        """Return the active API key used by the embedding provider."""
        if self.config_service is None:
            return config.OPENAI_API_KEY
        return self.config_service.get_api_key()

    def index_document(
        self,
        *,
        library_id: int,
        collection_name: str,
        document_id: int,
        text: str,
    ) -> list[dict]:
        """Create chunks for one document and write them into a library collection."""
        chunks = self.split_text(text, library_id)
        if not chunks:
            raise ValueError("No indexable text was extracted from the PDF.")

        indexed_chunks: list[dict] = []
        vector_store = self._get_vector_store(collection_name, library_id)
        created_vector_ids: list[str] = []
        embedding_model = self._get_embedding_model_name(library_id)

        try:
            for index, chunk_text in enumerate(chunks):
                vector_id = f"library-{library_id}-doc-{document_id}-chunk-{index}"
                vector_store.add_texts(
                    texts=[chunk_text],
                    metadatas=[
                        {
                            "library_id": library_id,
                            "document_id": document_id,
                            "chunk_index": index,
                        }
                    ],
                    ids=[vector_id],
                )
                created_vector_ids.append(vector_id)
                indexed_chunks.append(
                    {
                        "chunk_index": index,
                        "chunk_text": chunk_text,
                        "token_count": len(chunk_text),
                        "vector_id": vector_id,
                        "embedding_model": embedding_model,
                    }
                )
        except Exception:
            if created_vector_ids:
                try:
                    vector_store.delete(ids=created_vector_ids)
                except Exception:
                    # Best-effort cleanup only. The ingest layer will still mark
                    # the document as failed so a later sync can repair it.
                    pass
            raise

        return indexed_chunks

    def search(self, *, collection_name: str, library_id: int, query: str, top_k: int = 5):
        """Run similarity search inside one library collection."""
        vector_store = self._get_vector_store(collection_name, library_id)
        return vector_store.similarity_search(query, k=top_k)

    def delete_document_vectors(self, collection_name: str, library_id: int, document_id: int) -> None:
        """Best-effort removal of all vectors belonging to one document."""
        vector_store = self._get_vector_store(collection_name, library_id)
        try:
            vector_store.delete(where={"document_id": document_id})
        except Exception:
            return

    def delete_collection(self, collection_name: str, library_id: int | None = None) -> None:
        """Best-effort removal of one persisted Chroma collection."""
        matching_cache_keys = [key for key in self._vector_stores if key[0] == collection_name]
        vector_store = None
        if matching_cache_keys:
            vector_store = self._vector_stores.pop(matching_cache_keys[0], None)
            for key in matching_cache_keys[1:]:
                self._vector_stores.pop(key, None)
        if vector_store is None:
            vector_store = self._get_vector_store(collection_name, library_id)
            for key in [key for key in self._vector_stores if key[0] == collection_name]:
                self._vector_stores.pop(key, None)

        client = getattr(vector_store, "_client", None)
        if client is None:
            return

        try:
            client.delete_collection(name=collection_name)
        except Exception:
            # Deleting the SQLite records is the critical step. If Chroma cleanup
            # fails, we keep the request successful and leave only orphaned vectors.
            return
