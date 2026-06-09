from __future__ import annotations

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
                "semantic_chunking_enabled": effective_chunk_mode == "semantic",
            },
            "library_id": library_id,
        }

    def update_model_config(
        self,
        *,
        library_id: int | None,
        global_config: dict[str, object] | None = None,
        library_config: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Persist one or more layered config sections."""
        self._validate_library(library_id)

        pending_updates: dict[str, object] = {}
        if global_config is not None:
            normalized_global = self._normalize_global_config(global_config)
            pending_updates.update(
                {self._global_key(key): value for key, value in normalized_global.items()}
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

        self.config_repository.set_many_json_values(pending_updates)
        return self.get_model_config(library_id)

    def update_default_library_index_config(
        self,
        *,
        embedding_model: str,
        embedding_max_input_tokens: int,
    ) -> dict[str, object]:
        """保存新建文献库表单使用的默认向量配置。"""
        normalized_library = self._normalize_library_config(
            {
                "embedding_model": embedding_model,
                "embedding_max_input_tokens": embedding_max_input_tokens,
            }
        )
        self.config_repository.set_many_json_values(
            {
                self._global_key("embedding_model"): normalized_library["embedding_model"],
                self._global_key("embedding_max_input_tokens"): normalized_library[
                    "embedding_max_input_tokens"
                ],
            }
        )
        return self.get_model_config(None)

    def get_llm_model_name(self) -> str:
        return self._require_non_empty_config(
            self._merge_global_config()["llm_model"],
            "请先在模型配置中填写 LLM 模型。",
        )

    def get_embedding_model_name(self, library_id: int | None = None) -> str:
        if library_id is not None:
            return self._require_non_empty_config(
                self._get_library_index_config(library_id)["embedding_model"],
                "请先为当前文献库配置向量模型。",
            )
        return self._require_non_empty_config(
            self._merge_global_config()["embedding_model"],
            "请先选择文献库并配置向量模型。",
        )

    def get_api_key(self) -> str:
        return self._require_non_empty_config(
            self._merge_global_config()["api_key"],
            "请先在模型配置中填写 API_KEY。",
        )

    def get_llm_context_length(self) -> int:
        return self._require_positive_config_int(
            self._merge_global_config()["llm_context_length"],
            "请先在模型配置中填写有效的 LLM 上下文长度。",
        )

    def get_embedding_max_input_tokens(self, library_id: int | None = None) -> int:
        if library_id is not None:
            return self._require_positive_config_int(
                self._get_library_index_config(library_id)["embedding_max_input_tokens"],
                "请先为当前文献库配置向量模型最大输入 Token 数。",
            )
        return self._require_positive_config_int(
            self._merge_global_config()["embedding_max_input_tokens"],
            "请先选择文献库并配置向量模型最大输入 Token 数。",
        )

    def get_requested_chunk_mode(self, library_id: int | None) -> str:
        return str(self._get_library_index_config(library_id)["chunk_mode"])

    def get_effective_chunk_mode(self, library_id: int | None) -> str:
        """Return the chunk mode the runtime can actually execute."""
        return self._get_library_chunk_mode(library_id)

    def _merge_global_config(self) -> dict[str, object]:
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
            "llm_model": self._as_optional_str(payloads.get(self._global_key("llm_model"))),
            "embedding_model": self._as_optional_str(payloads.get(self._global_key("embedding_model"))),
            "api_key": self._as_optional_str(payloads.get(self._global_key("api_key"))),
            "llm_context_length": self._as_optional_positive_int(
                payloads.get(self._global_key("llm_context_length")),
            ),
            "embedding_max_input_tokens": self._as_optional_positive_int(
                payloads.get(self._global_key("embedding_max_input_tokens")),
            ),
        }

    def _get_library_chunk_mode(self, library_id: int | None) -> str:
        return str(self._get_library_index_config(library_id)["chunk_mode"])

    def _get_library_index_config(self, library_id: int | None) -> dict[str, object]:
        if library_id is None:
            return {
                "embedding_model": "",
                "embedding_max_input_tokens": None,
                "chunk_mode": "recursive",
            }

        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")

        chunk_mode = self._as_non_empty_str(getattr(library, "chunk_mode", None), "recursive")
        if chunk_mode not in self.SUPPORTED_CHUNK_MODES:
            chunk_mode = "recursive"

        return {
            "embedding_model": self._as_optional_str(getattr(library, "embedding_model", None)),
            "embedding_max_input_tokens": self._as_optional_positive_int(
                getattr(library, "embedding_max_input_tokens", None),
            ),
            "chunk_mode": chunk_mode,
        }

    def _normalize_global_config(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "llm_model": self._require_non_empty_config(
                payload.get("llm_model"),
                "llm_model cannot be empty.",
            ),
            "api_key": self._require_non_empty_config(
                payload.get("api_key"),
                "api_key cannot be empty.",
            ),
            "llm_context_length": self._require_positive_int(
                payload.get("llm_context_length"),
                "llm_context_length",
                None,
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
                None,
            )

        if payload.get("chunk_mode") is not None:
            chunk_mode = self._as_non_empty_str(payload.get("chunk_mode"), "recursive")
            if chunk_mode not in self.SUPPORTED_CHUNK_MODES:
                raise ValueError(f"Unsupported chunk_mode: {chunk_mode}")
            normalized["chunk_mode"] = chunk_mode

        return normalized

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
    def _as_optional_str(value: object) -> str:
        """把数据库配置值转换为 UI 可展示字符串，缺失时返回空字符串。"""
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _as_non_empty_str(value: object, default: str) -> str:
        """读取兼容配置字符串；只在非模型默认值场景使用传入的业务默认值。"""
        if value is None:
            return default
        normalized = str(value).strip()
        return normalized or default

    @staticmethod
    def _as_optional_positive_int(value: object) -> int | None:
        """把数据库配置值转换为正整数；缺失或非法时返回 None 供 UI 显示未配置。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _require_non_empty_config(value: object, message: str) -> str:
        """业务调用配置时强制要求非空字符串，避免静默使用模型默认值。"""
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(message)
        return normalized

    @staticmethod
    def _require_positive_config_int(value: object, message: str) -> int:
        """业务调用配置时强制要求正整数，避免静默使用分块默认值。"""
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(message) from exc
        if parsed <= 0:
            raise ValueError(message)
        return parsed

    @staticmethod
    def _require_positive_int(value: object, field_name: str, default: int | None = None) -> int:
        if value is None:
            if default is None:
                raise ValueError(f"{field_name} must be a positive integer.")
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a positive integer.") from exc
        if parsed <= 0:
            raise ValueError(f"{field_name} must be a positive integer.")
        return parsed
