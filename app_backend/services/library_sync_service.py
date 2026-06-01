from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
import json
from pathlib import Path
import threading

import config_data as config
from app_backend.models import LibraryRecord
from app_backend.repositories.document_repository import DocumentRepository
from app_backend.repositories.library_repository import LibraryRepository
from app_backend.repositories.sync_repository import SyncRepository
from app_backend.services.citation_formatter import format_gbt7714_citation
from app_backend.services.document_ingest_service import DocumentIngestService
from app_backend.services.vector_index_service import VectorIndexService


class LibrarySyncService:
    """Library management and synchronization service.

    Design goals:
    - sessions reuse persistent library indexes instead of rebuilding them
    - each library owns its own Chroma collection and local folder config
    - sync remains incremental by deduplicating on file hash within a library
    """

    def __init__(
        self,
        ingest_service: DocumentIngestService,
        sync_repository: SyncRepository,
        library_repository: LibraryRepository,
        document_repository: DocumentRepository,
        vector_index_service: VectorIndexService,
    ) -> None:
        """Initialize the library management service."""
        self.ingest_service = ingest_service
        self.sync_repository = sync_repository
        self.library_repository = library_repository
        self.document_repository = document_repository
        self.vector_index_service = vector_index_service
        self._sync_state_lock = threading.Lock()
        self._job_states: dict[int, dict] = {}
        self._running_jobs_by_library: dict[int, int] = {}

    def get_first_library(self) -> LibraryRecord | None:
        """Return the oldest existing library, or `None` when none exists."""
        return self.library_repository.get_first_library()

    def list_libraries(self) -> list[dict]:
        """List all libraries together with simple document counts."""
        libraries = self.library_repository.list_libraries()
        return [
            {
                **library.__dict__,
                "document_count": self.document_repository.count_documents(library.id),
            }
            for library in libraries
        ]

    def get_library(self, library_id: int) -> dict:
        """Return one library with its current document count."""
        library = self._require_library(library_id)
        return {
            **library.__dict__,
            "document_count": self.document_repository.count_documents(library.id),
        }

    def get_library_details(self, library_id: int) -> dict:
        """Return one library together with lightweight document details."""
        library = self._require_library(library_id)
        return {
            **library.__dict__,
            "document_count": self.document_repository.count_documents(library.id),
            "documents": self.document_repository.list_document_summaries(library.id),
        }

    def get_document_details(self, library_id: int, document_id: int) -> dict:
        """Return the structured metadata for one document inside a library."""
        library = self._require_library(library_id)
        document = self.document_repository.get_by_id(document_id)
        if document is None or document.library_id != library.id:
            raise ValueError(f"Document not found in library: {document_id}")

        authors = self._parse_json_list(document.authors_json)
        return {
            "id": document.id,
            "library_id": document.library_id,
            "file_hash": document.file_hash,
            "file_path": document.file_path,
            "file_name": document.file_name,
            "title": document.title,
            "abstract": document.abstract,
            "authors": authors,
            "keywords": self._parse_json_list(document.keywords_json),
            "year": document.year,
            "doi": document.doi,
            "url": document.url,
            "venue": document.venue,
            "citation_text_default": self._format_document_citation(
                authors=authors,
                title=document.title,
                year=document.year,
                venue=document.venue,
                doi=document.doi,
                url=document.url,
                source_type=document.source_type,
                fallback=document.citation_text_default,
            ),
            "source_type": document.source_type,
            "source_uri": document.source_uri,
            "status": document.status,
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        }

    def create_library(
        self,
        *,
        name: str,
        description: str = "",
        folder_path: str = "",
        embedding_model: str = config.EMBEDDING_MODEL_NAME,
        embedding_max_input_tokens: int = config.DOCUMENT_CHUNK_MAX_CHARS,
        chunk_mode: str = "recursive",
    ) -> dict:
        """Create a new logical library."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Library name cannot be empty.")
        normalized_embedding_model = embedding_model.strip()
        if not normalized_embedding_model:
            raise ValueError("Embedding model cannot be empty.")
        try:
            normalized_embedding_max_input_tokens = int(embedding_max_input_tokens)
        except (TypeError, ValueError) as exc:
            raise ValueError("embedding_max_input_tokens must be a positive integer.") from exc
        if normalized_embedding_max_input_tokens <= 0:
            raise ValueError("embedding_max_input_tokens must be a positive integer.")
        normalized_chunk_mode = chunk_mode.strip() or "recursive"
        if normalized_chunk_mode not in {"recursive", "semantic"}:
            raise ValueError(f"Unsupported chunk_mode: {normalized_chunk_mode}")
        normalized_folder = self._normalize_optional_folder(folder_path)
        library = self.library_repository.create_library(
            name=normalized_name,
            description=description.strip(),
            folder_path=normalized_folder,
            embedding_model=normalized_embedding_model,
            embedding_max_input_tokens=normalized_embedding_max_input_tokens,
            chunk_mode=normalized_chunk_mode,
        )
        return {
            **library.__dict__,
            "document_count": 0,
        }

    def update_library(
        self,
        library_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        folder_path: str | None = None,
    ) -> dict:
        """Update basic library metadata and optional folder binding."""
        self._require_library(library_id)
        normalized_folder = (
            self._normalize_optional_folder(folder_path) if folder_path is not None else None
        )
        updated = self.library_repository.update_library(
            library_id,
            name=name.strip() if name is not None else None,
            description=description.strip() if description is not None else None,
            folder_path=normalized_folder,
        )
        if not updated:
            raise ValueError("No library fields were updated.")
        return self.get_library(library_id)

    def delete_library(self, library_id: int) -> None:
        """Delete one library when no chat session still depends on it."""
        library = self._require_library(library_id)
        session_count = self.library_repository.count_sessions_for_library(library_id)
        if session_count > 0:
            raise ValueError("This library is still used by one or more sessions and cannot be deleted.")

        self.vector_index_service.delete_collection(library.collection_name, library.id)

        deleted = self.library_repository.delete_library(library_id)
        if not deleted:
            raise ValueError(f"Library not found: {library_id}")

    def delete_document(self, library_id: int, document_id: int) -> None:
        """Delete one document from a library together with chunks and vectors."""
        library = self._require_library(library_id)
        document = self.document_repository.get_by_id(document_id)
        if document is None or document.library_id != library.id:
            raise ValueError(f"Document not found in library: {document_id}")

        self.sync_repository.delete_items_for_document(document.id)
        self.document_repository.delete_chunks(document.id)
        self.vector_index_service.delete_document_vectors(library.collection_name, library.id, document.id)

        deleted = self.document_repository.delete_document(document.id)
        if not deleted:
            raise ValueError(f"Document not found in library: {document_id}")

    def configure_folder(self, library_id: int, folder_path: str) -> dict:
        """Bind a local folder to a specific library."""
        normalized_path = self._normalize_required_folder(folder_path)
        updated = self.library_repository.update_library(
            library_id,
            folder_path=normalized_path,
        )
        if not updated:
            raise ValueError(f"Library not found: {library_id}")
        return self.get_library(library_id)

    def get_configured_folder(self, library_id: int | None = None) -> str | None:
        """Return the configured folder for one library."""
        library = self.get_first_library() if library_id is None else self._require_library(library_id)
        if library is None:
            return None
        return library.folder_path or None

    def start_sync_job(
        self,
        library_id: int,
        folder_path: str | None = None,
        job_type: str = "incremental",
    ) -> dict:
        """Start one background sync thread and return the job status payload."""
        library = self._require_library(library_id)
        normalized_path = self._resolve_sync_folder(library, folder_path)
        pdf_paths = self._list_pdf_paths(normalized_path)

        with self._sync_state_lock:
            running_job_id = self._running_jobs_by_library.get(library.id)
            if running_job_id is not None:
                existing_status = self.get_sync_job_status(running_job_id)
                existing_status["already_running"] = True
                return existing_status

            started_at = datetime.now().isoformat(timespec="seconds")
            job_id = self.sync_repository.create_job(library.id, normalized_path, job_type)
            self._running_jobs_by_library[library.id] = job_id
            self._job_states[job_id] = {
                "job_id": job_id,
                "library_id": library.id,
                "status": "running",
                "is_running": True,
                "already_running": False,
                "library": self.get_library(library.id),
                "paper_folder": normalized_path,
                "file_count": len(pdf_paths),
                "new_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "results": [],
                "current_index": 0,
                "total_count": 0,
                "current_file_name": "",
                "current_file_path": "",
                "error_message": "",
                "started_at": started_at,
                "finished_at": None,
            }

        worker = threading.Thread(
            target=self._run_background_sync_job,
            kwargs={
                "job_id": job_id,
                "library_id": library.id,
                "normalized_path": normalized_path,
                "job_type": job_type,
            },
            daemon=True,
            name=f"library-sync-{library.id}-{job_id}",
        )
        worker.start()
        return self.get_sync_job_status(job_id)

    def get_sync_job_status(self, job_id: int) -> dict:
        """Return one sync job status, including live in-memory progress when running."""
        with self._sync_state_lock:
            live_state = self._job_states.get(job_id)
            if live_state is not None:
                return dict(live_state)

        job_row = self.sync_repository.get_job(job_id)
        if job_row is None:
            raise ValueError(f"Sync job not found: {job_id}")

        item_rows = self.sync_repository.list_items(job_id)
        fallback_status = job_row["status"]
        if fallback_status == "running":
            fallback_status = "failed"
            if not job_row["error_message"]:
                job_row["error_message"] = "The sync worker is no longer running."

        library_id = int(job_row["library_id"])
        library = self.library_repository.get_by_id(library_id)

        return {
            "job_id": int(job_row["id"]),
            "library_id": library_id,
            "status": fallback_status,
            "is_running": False,
            "already_running": False,
            "library": library.__dict__ if library is not None else None,
            "paper_folder": job_row["folder_path"],
            "file_count": int(job_row["scanned_count"]),
            "new_count": int(job_row["new_count"]),
            "skipped_count": int(job_row["skipped_count"]),
            "failed_count": int(job_row["failed_count"]),
            "results": [
                {
                    "path": item["file_path"],
                    "success": item["status"] in {"saved", "duplicate"},
                    "status": item["status"],
                    "library_id": library_id,
                    "file_hash": item["file_hash"],
                    "document_id": item["document_id"],
                    "error": item["message"],
                }
                for item in item_rows
            ],
            "current_index": 0,
            "total_count": 0,
            "current_file_name": "",
            "current_file_path": "",
            "error_message": job_row["error_message"],
            "started_at": job_row["started_at"],
            "finished_at": job_row["finished_at"],
        }

    def sync_library(
        self,
        library_id: int,
        folder_path: str | None = None,
        job_type: str = "incremental",
        ) -> dict:
        """Synchronize all PDFs from a library folder into that library."""
        _, sync_result = self._run_sync(
            library_id,
            folder_path=folder_path,
            job_type=job_type,
        )
        return sync_result

    def sync_library_stream(
        self,
        library_id: int,
        folder_path: str | None = None,
        job_type: str = "incremental",
    ) -> Iterator[dict]:
        """Synchronize one library and yield progress events for new files."""
        library = self._require_library(library_id)
        normalized_path = self._resolve_sync_folder(library, folder_path)
        pdf_paths = sorted(str(path.resolve()) for path in Path(normalized_path).rglob("*.pdf"))
        if not pdf_paths:
            raise FileNotFoundError("No PDF files were found in the configured library folder.")

        job_id = self.sync_repository.create_job(library.id, normalized_path, job_type)
        results = []
        new_count = 0
        skipped_count = 0
        failed_count = 0
        path_states = [
            (pdf_path, self._lookup_existing_document(library.id, pdf_path))
            for pdf_path in pdf_paths
        ]
        pending_new_count = sum(1 for _, existing_document in path_states if existing_document is None)
        current_new_index = 0

        for pdf_path, existing_document in path_states:
            if existing_document is None:
                current_new_index += 1
                yield {
                    "type": "progress",
                    "library_id": library.id,
                    "file_name": Path(pdf_path).name,
                    "path": pdf_path,
                    "current_index": current_new_index,
                    "total_count": pending_new_count,
                }

            result = self.ingest_service.ingest_path(
                pdf_path,
                source_type="local_folder",
                library_id=library.id,
            )
            results.append(result)

            if result.status == "saved":
                new_count += 1
            elif result.status == "duplicate":
                skipped_count += 1
            else:
                failed_count += 1

            self.sync_repository.add_item(
                job_id=job_id,
                file_path=result.path,
                file_hash=result.file_hash,
                document_id=result.document_id,
                status=result.status,
                message=result.error,
            )

        self.sync_repository.finish_job(
            job_id=job_id,
            status="finished",
            scanned_count=len(pdf_paths),
            new_count=new_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

        yield {
            "type": "done",
            "job_id": job_id,
            "library": self.get_library(library.id),
            "paper_folder": normalized_path,
            "file_count": len(pdf_paths),
            "new_count": new_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "results": [result.__dict__ for result in results],
        }

    def _run_sync(
        self,
        library_id: int,
        *,
        folder_path: str | None,
        job_type: str,
        emit_progress: bool = False,
    ) -> tuple[list[dict], dict]:
        """Run one sync job and optionally collect per-file progress events."""
        library = self._require_library(library_id)
        normalized_path = self._resolve_sync_folder(library, folder_path)
        pdf_paths = sorted(str(path.resolve()) for path in Path(normalized_path).rglob("*.pdf"))
        if not pdf_paths:
            raise FileNotFoundError("No PDF files were found in the configured library folder.")

        job_id = self.sync_repository.create_job(library.id, normalized_path, job_type)
        progress_events: list[dict] = []
        results = []
        new_count = 0
        skipped_count = 0
        failed_count = 0
        path_states = [
            (pdf_path, self._lookup_existing_document(library.id, pdf_path))
            for pdf_path in pdf_paths
        ]
        pending_new_count = sum(1 for _, existing_document in path_states if existing_document is None)
        current_new_index = 0
        for pdf_path, existing_document in path_states:
            if emit_progress and existing_document is None:
                current_new_index += 1
                progress_events.append(
                    {
                        "type": "progress",
                        "library_id": library.id,
                        "file_name": f"{current_new_index}/{pending_new_count}：{Path(pdf_path).name}",
                        "path": pdf_path,
                        "current_index": current_new_index,
                        "total_count": pending_new_count,
                    }
                )

            result = self.ingest_service.ingest_path(
                pdf_path,
                source_type="local_folder",
                library_id=library.id,
            )
            results.append(result)

            if result.status == "saved":
                new_count += 1
            elif result.status == "duplicate":
                skipped_count += 1
            else:
                failed_count += 1

            self.sync_repository.add_item(
                job_id=job_id,
                file_path=result.path,
                file_hash=result.file_hash,
                document_id=result.document_id,
                status=result.status,
                message=result.error,
            )

        self.sync_repository.finish_job(
            job_id=job_id,
            status="finished",
            scanned_count=len(pdf_paths),
            new_count=new_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
        )

        sync_result = {
            "job_id": job_id,
            "library": self.get_library(library.id),
            "paper_folder": normalized_path,
            "file_count": len(pdf_paths),
            "new_count": new_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "results": [result.__dict__ for result in results],
        }
        return progress_events, sync_result

    def _run_background_sync_job(
        self,
        *,
        job_id: int,
        library_id: int,
        normalized_path: str,
        job_type: str,
    ) -> None:
        """Execute one sync job inside a background thread."""
        file_count = 0
        new_count = 0
        skipped_count = 0
        failed_count = 0
        results: list[dict] = []
        pending_new_count = 0
        current_new_index = 0

        try:
            library = self._require_library(library_id)
            pdf_paths = self._list_pdf_paths(normalized_path)
            file_count = len(pdf_paths)
            path_states = [
                (pdf_path, self._lookup_existing_document(library.id, pdf_path))
                for pdf_path in pdf_paths
            ]
            pending_new_count = sum(1 for _, existing_document in path_states if existing_document is None)
            self._update_job_state(
                job_id,
                library=self.get_library(library.id),
                paper_folder=normalized_path,
                file_count=file_count,
                total_count=pending_new_count,
            )

            for pdf_path, existing_document in path_states:
                if existing_document is None:
                    current_new_index += 1
                    self._update_job_state(
                        job_id,
                        current_index=current_new_index,
                        total_count=pending_new_count,
                        current_file_name=Path(pdf_path).name,
                        current_file_path=pdf_path,
                    )

                result = self.ingest_service.ingest_path(
                    pdf_path,
                    source_type="local_folder",
                    library_id=library.id,
                )
                result_payload = result.__dict__
                results.append(result_payload)

                if result.status == "saved":
                    new_count += 1
                elif result.status == "duplicate":
                    skipped_count += 1
                else:
                    failed_count += 1

                self.sync_repository.add_item(
                    job_id=job_id,
                    file_path=result.path,
                    file_hash=result.file_hash,
                    document_id=result.document_id,
                    status=result.status,
                    message=result.error,
                )
                self._update_job_state(
                    job_id,
                    new_count=new_count,
                    skipped_count=skipped_count,
                    failed_count=failed_count,
                    results=list(results),
                )

            self.sync_repository.finish_job(
                job_id=job_id,
                status="finished",
                scanned_count=file_count,
                new_count=new_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
            )
            self._update_job_state(
                job_id,
                status="finished",
                is_running=False,
                library=self.get_library(library.id),
                paper_folder=normalized_path,
                file_count=file_count,
                new_count=new_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                results=list(results),
                current_index=current_new_index,
                total_count=pending_new_count,
                current_file_name="",
                current_file_path="",
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )
        except Exception as exc:
            self.sync_repository.finish_job(
                job_id=job_id,
                status="failed",
                scanned_count=file_count,
                new_count=new_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                error_message=str(exc),
            )
            self._update_job_state(
                job_id,
                status="failed",
                is_running=False,
                file_count=file_count,
                new_count=new_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                results=list(results),
                current_index=current_new_index,
                total_count=pending_new_count,
                error_message=str(exc),
                current_file_name="",
                current_file_path="",
                finished_at=datetime.now().isoformat(timespec="seconds"),
            )
        finally:
            with self._sync_state_lock:
                running_job_id = self._running_jobs_by_library.get(library_id)
                if running_job_id == job_id:
                    self._running_jobs_by_library.pop(library_id, None)

    def _update_job_state(self, job_id: int, **updates) -> None:
        """Merge one partial progress update into the in-memory job state."""
        with self._sync_state_lock:
            state = self._job_states.get(job_id)
            if state is None:
                return
            state.update(updates)

    @staticmethod
    def _list_pdf_paths(folder_path: str) -> list[str]:
        """Return all PDF paths for one library folder."""
        pdf_paths = sorted(str(path.resolve()) for path in Path(folder_path).rglob("*.pdf"))
        if not pdf_paths:
            raise FileNotFoundError("No PDF files were found in the configured library folder.")
        return pdf_paths

    @staticmethod
    def _parse_json_list(raw_value: str) -> list[str]:
        """Parse one stored JSON list field into a Python list."""
        if not raw_value.strip():
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in parsed] if isinstance(parsed, list) else []

    @staticmethod
    def _format_document_citation(
        *,
        authors: list[str],
        title: str,
        year: str,
        venue: str,
        doi: str,
        url: str,
        source_type: str,
        fallback: str,
    ) -> str:
        """为文献详情接口生成近似 GB/T 7714-2015 的引用文本。"""
        citation = format_gbt7714_citation(
            authors=authors,
            title=title,
            year=year,
            venue=venue,
            doi=doi,
            url=url,
            source_type=source_type or "local",
        )
        return citation or fallback

    def _require_library(self, library_id: int) -> LibraryRecord:
        """Load a library or raise a helpful error."""
        library = self.library_repository.get_by_id(library_id)
        if library is None:
            raise ValueError(f"Library not found: {library_id}")
        return library

    def _lookup_existing_document(self, library_id: int, pdf_path: str) -> object | None:
        """Return the existing library document for one file hash when present."""
        file_hash = self.ingest_service.compute_file_hash(pdf_path)
        return self.document_repository.get_by_file_hash(library_id, file_hash)

    def _resolve_sync_folder(self, library: LibraryRecord, folder_path: str | None) -> str:
        """Resolve the effective folder used by one sync request."""
        if folder_path is not None:
            normalized_path = self._normalize_required_folder(folder_path)
            self.library_repository.update_library(library.id, folder_path=normalized_path)
            return normalized_path

        if library.folder_path:
            return self._normalize_required_folder(library.folder_path)

        raise FileNotFoundError("This library does not have a configured local folder yet.")

    @staticmethod
    def _normalize_required_folder(folder_path: str) -> str:
        """Normalize and validate a required library folder path."""
        path = Path(folder_path).resolve()
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Library folder does not exist: {path}")
        return str(path)

    @staticmethod
    def _normalize_optional_folder(folder_path: str) -> str:
        """Normalize an optional folder path, allowing the empty string."""
        if not folder_path.strip():
            return ""
        return LibrarySyncService._normalize_required_folder(folder_path)
