from __future__ import annotations

import config_data as config
from app_backend.repositories.config_repository import ConfigRepository
from app_backend.repositories.library_repository import LibraryRepository


class ConfigService:
    """Read and persist layered runtime configuration."""

    SUPPORTED_CHUNK_MODES = {"recursive", "semantic"}

    def __init__(
        self,
        config_repository: ConfigRepository,
        library_repository: LibraryRepository,
    ) -> None:
        self.config_repository = config_repository
        self.library_repository = library_repository

    def get_model_config(self, library_id: int | None = None) -> dict[str, object]:
        """Return the layered model configuration for the UI."""
        self._validate_library(library_id)

        global_config = self._merge_global_config()
        session_config = self._merge_session_config()
        library_config = self._get_library_index_config(library_id)
        requested_chunk_mode = str(library_config["chunk_mode"])
        effective_chunk_mode = self.get_effective_chunk_mode(library_id)

        return {
            "global": global_config,
            "library": {
                "embedding_model": library_config["embedding_model"],
                "embedding_max_input_tokens": library_config["embedding_max_input_tokens"],
                "chunk_mode": requested_chunk_mode,
                "effective_chunk_mode": effective_chunk_mode,
                "semantic_chunking_enabled": False,
            },
            "session": session_config,
            "library_id": library_id,
        }

    def update_model_config(
        self,
        *,
        library_id: int | None,
        global_config: dict[str, object] | None = None,
        library_config: dict[str, object] | None = None,
        session_config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Persist one or more layered config sections."""
        self._validate_library(library_id)

        pending_updates: dict[str, object] = {}
        if global_config is not None:
            normalized_global = self._normalize_global_config(global_config)
            pending_updates.update(
                {
                    self._global_key("llm_model"): normalized_global["llm_model"],
                    self._global_key("embedding_model"): normalized_global["embedding_model"],
                    self._global_key("api_key"): normalized_global["api_key"],
                    self._global_key("llm_context_length"): normalized_global["llm_context_length"],
                    self._global_key("embedding_max_input_tokens"): normalized_global["embedding_max_input_tokens"],
                }
            )

        if library_config is not None:
            if library_id is None:
                raise ValueError("Library configuration requires a concrete library_id.")
            normalized_library = self._normalize_library_config(library_config)
            if normalized_library:
                updated = self.library_repository.update_library(
                    library_id,
                    embedding_model=normalized_library.get("embedding_model"),
                    embedding_max_input_tokens=normalized_library.get("embedding_max_input_tokens"),
                    chunk_mode=normalized_library.get("chunk_mode"),
                )
                if not updated:
                    raise ValueError("No library index fields were updated.")

        if session_config is not None:
            normalized_session = self._normalize_session_config(session_config)
            pending_updates[self._session_key("recall_chunks")] = normalized_session["recall_chunks"]
            pending_updates[self._session_key("rerank_chunks")] = normalized_session["rerank_chunks"]

        self.config_repository.set_many_json_values(pending_updates)
        return self.get_model_config(library_id)

    def get_llm_model_name(self) -> str:
        return str(self._merge_global_config()["llm_model"])

    def get_embedding_model_name(self, library_id: int | None = None) -> str:
        if library_id is not None:
            return str(self._get_library_index_config(library_id)["embedding_model"])
        return str(self._merge_global_config()["embedding_model"])

    def get_api_key(self) -> str:
        return str(self._merge_global_config()["api_key"])

    def get_llm_context_length(self) -> int:
        return int(self._merge_global_config()["llm_context_length"])

    def get_embedding_max_input_tokens(self, library_id: int | None = None) -> int:
        if library_id is not None:
            return int(self._get_library_index_config(library_id)["embedding_max_input_tokens"])
        return int(self._merge_global_config()["embedding_max_input_tokens"])

    def get_recall_chunks(self) -> int:
        return int(self._merge_session_config()["recall_chunks"])

    def get_rerank_chunks(self) -> int:
        return int(self._merge_session_config()["rerank_chunks"])

    def get_requested_chunk_mode(self, library_id: int | None) -> str:
        return str(self._get_library_index_config(library_id)["chunk_mode"])

    def get_effective_chunk_mode(self, library_id: int | None) -> str:
        """Return the chunk mode the runtime can actually execute."""
        requested_mode = self._get_library_chunk_mode(library_id)
        if requested_mode == "semantic":
            return "recursive"
        return requested_mode

    def _merge_global_config(self) -> dict[str, object]:
        defaults = {
            "llm_model": config.LLM_MODEL_NAME,
            "embedding_model": config.EMBEDDING_MODEL_NAME,
            "api_key": config.OPENAI_API_KEY,
            "llm_context_length": 200000,
            "embedding_max_input_tokens": 2048,
        }
        payloads = self.config_repository.get_many_json_values(
            [
                self._global_key("llm_model"),
                self._global_key("embedding_model"),
                self._global_key("api_key"),
                self._global_key("llm_context_length"),
                self._global_key("embedding_max_input_tokens"),
            ]
        )
        return {
            "llm_model": self._as_non_empty_str(payloads.get(self._global_key("llm_model")), defaults["llm_model"]),
            "embedding_model": self._as_non_empty_str(
                payloads.get(self._global_key("embedding_model")),
                defaults["embedding_model"],
            ),
            "api_key": self._as_str(payloads.get(self._global_key("api_key")), defaults["api_key"]),
            "llm_context_length": self._as_positive_int(
                payloads.get(self._global_key("llm_context_length")),
                int(defaults["llm_context_length"]),
            ),
            "embedding_max_input_tokens": self._as_positive_int(
                payloads.get(self._global_key("embedding_max_input_tokens")),
                int(defaults["embedding_max_input_tokens"]),
            ),
        }

    def _merge_session_config(self) -> dict[str, object]:
        defaults = {
            "recall_chunks": 20,
            "rerank_chunks": 5,
        }
        payloads = self.config_repository.get_many_json_values(
            [
                self._session_key("recall_chunks"),
                self._session_key("rerank_chunks"),
            ]
        )
        return {
            "recall_chunks": self._as_positive_int(payloads.get(self._session_key("recall_chunks")), defaults["recall_chunks"]),
            "rerank_chunks": self._as_positive_int(payloads.get(self._session_key("rerank_chunks")), defaults["rerank_chunks"]),
        }

    def _get_library_chunk_mode(self, library_id: int | None) -> str:
        return str(self._get_library_index_config(library_id)["chunk_mode"])

    def _get_library_index_config(self, library_id: int | None) -> dict[str, object]:
        defaults = self._merge_global_config()
        if library_id is None:
            return {
                "embedding_model": str(defaults["embedding_model"]),
                "embedding_max_input_tokens": int(defaults["embedding_max_input_tokens"]),
                "chunk_mode": "recursive",
            }

        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

        chunk_mode = self._as_non_empty_str(getattr(library, "chunk_mode", None), "recursive")
        if chunk_mode not in self.SUPPORTED_CHUNK_MODES:
            chunk_mode = "recursive"

        return {
            "embedding_model": self._as_non_empty_str(
                getattr(library, "embedding_model", None),
                str(defaults["embedding_model"]),
            ),
            "embedding_max_input_tokens": self._as_positive_int(
                getattr(library, "embedding_max_input_tokens", None),
                int(defaults["embedding_max_input_tokens"]),
            ),
            "chunk_mode": chunk_mode,
        }

    def _normalize_global_config(self, payload: dict[str, object]) -> dict[str, object]:
        merged = self._merge_global_config()
        return {
            "llm_model": self._as_non_empty_str(payload.get("llm_model"), str(merged["llm_model"])),
            "embedding_model": self._as_non_empty_str(payload.get("embedding_model"), str(merged["embedding_model"])),
            "api_key": self._as_str(payload.get("api_key"), str(merged["api_key"])),
            "llm_context_length": self._require_positive_int(
                payload.get("llm_context_length"),
                "llm_context_length",
                int(merged["llm_context_length"]),
            ),
            "embedding_max_input_tokens": self._require_positive_int(
                payload.get("embedding_max_input_tokens"),
                "embedding_max_input_tokens",
                int(merged["embedding_max_input_tokens"]),
            ),
        }

    def _normalize_library_config(self, payload: dict[str, object]) -> dict[str, object]:
        normalized: dict[str, object] = {}

        if payload.get("embedding_model") is not None:
            embedding_model = self._as_non_empty_str(payload.get("embedding_model"), "")
            if not embedding_model:
                raise ValueError("embedding_model cannot be empty.")
            normalized["embedding_model"] = embedding_model

        if payload.get("embedding_max_input_tokens") is not None:
            normalized["embedding_max_input_tokens"] = self._require_positive_int(
                payload.get("embedding_max_input_tokens"),
                "embedding_max_input_tokens",
                2048,
            )

        if payload.get("chunk_mode") is not None:
            chunk_mode = self._as_non_empty_str(payload.get("chunk_mode"), "recursive")
            if chunk_mode not in self.SUPPORTED_CHUNK_MODES:
                raise ValueError(f"Unsupported chunk_mode: {chunk_mode}")
            normalized["chunk_mode"] = chunk_mode

        return normalized

    def _normalize_session_config(self, payload: dict[str, object]) -> dict[str, object]:
        merged = self._merge_session_config()
        recall_chunks = self._require_positive_int(
            payload.get("recall_chunks"),
            "recall_chunks",
            int(merged["recall_chunks"]),
        )
        rerank_chunks = self._require_positive_int(
            payload.get("rerank_chunks"),
            "rerank_chunks",
            int(merged["rerank_chunks"]),
        )
        if recall_chunks < rerank_chunks:
            raise ValueError("recall_chunks must be greater than or equal to rerank_chunks.")
        return {
            "recall_chunks": recall_chunks,
            "rerank_chunks": rerank_chunks,
        }

    def _validate_library(self, library_id: int | None) -> None:
        if library_id is None:
            return
        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

    @staticmethod
    def _global_key(name: str) -> str:
        return f"global.{name}"

    @staticmethod
    def _session_key(name: str) -> str:
        return f"session.{name}"

    @staticmethod
    def _as_str(value: object, default: str) -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _as_non_empty_str(value: object, default: str) -> str:
        if value is None:
            return default
        normalized = str(value).strip()
        return normalized or default

    @staticmethod
    def _as_positive_int(value: object, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _require_positive_int(value: object, field_name: str, default: int) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a positive integer.") from exc
        if parsed <= 0:
            raise ValueError(f"{field_name} must be a positive integer.")
        return parsed
