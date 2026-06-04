from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config_data as config
from app_backend.bootstrap import ServiceContainer

app = FastAPI(title="RAG Paper Assistant API")
container = ServiceContainer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigureFolderRequest(BaseModel):
    library_id: int | None = None
    folder_path: str | None = None


class CreateLibraryRequest(BaseModel):
    name: str
    description: str = ""
    folder_path: str = ""
    embedding_model: str
    embedding_max_input_tokens: int
    chunk_mode: str


class UpdateLibraryRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    folder_path: str | None = None


class CreateSessionRequest(BaseModel):
    title: str
    user_goal: str
    library_id: int | None = None


class UpdateSessionRequest(BaseModel):
    title: str | None = None
    is_pinned: bool | None = None
    library_id: int | None = None


class ChatRequest(BaseModel):
    message: str
    top_k: int = config.RECALL_K
    allow_external_search: bool = False


class CreateMemoryRequest(BaseModel):
    scope: str
    memory_type: str
    content: str
    summary: str
    session_id: int | None = None
    importance: int = 1


class GlobalModelConfigPayload(BaseModel):
    llm_model: str
    api_key: str
    llm_context_length: int


class LibraryModelConfigPayload(BaseModel):
    embedding_model: str | None = None
    embedding_max_input_tokens: int | None = None
    chunk_mode: str | None = None


class SessionModelConfigPayload(BaseModel):
    recall_chunks: int
    rerank_chunks: int


class UpdateModelConfigRequest(BaseModel):
    library_id: int | None = None
    global_config: GlobalModelConfigPayload | None = None
    library_config: LibraryModelConfigPayload | None = None
    session_config: SessionModelConfigPayload | None = None


def resolve_library_id(library_id: int | None) -> int:
    """Resolve a nullable library id to a concrete target library id."""
    if library_id is not None:
        return library_id
    raise HTTPException(status_code=400, detail="Please choose a library first.")


def resolve_configured_folder(library_id: int | None, folder_path: str | None) -> tuple[int, str]:
    """Resolve the effective library id and folder path for a sync request."""
    resolved_library_id = resolve_library_id(library_id)
    if folder_path:
        return resolved_library_id, folder_path

    configured = container.library_sync_service.get_configured_folder(resolved_library_id)
    if not configured:
        raise HTTPException(status_code=400, detail="This library does not have a configured local folder yet.")
    return resolved_library_id, configured


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/api/libraries")
def list_libraries() -> dict[str, object]:
    """List all configured libraries."""
    return {"libraries": container.library_sync_service.list_libraries()}


@app.get("/api/model-config")
def get_model_config(library_id: int | None = None) -> dict[str, object]:
    """Return the layered model configuration for the settings UI."""
    try:
        model_config = container.config_service.get_model_config(library_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "config": model_config}


@app.patch("/api/model-config")
def update_model_config(payload: UpdateModelConfigRequest) -> dict[str, object]:
    """Persist the layered model configuration."""
    try:
        model_config = container.config_service.update_model_config(
            library_id=payload.library_id,
            global_config=payload.global_config.model_dump() if payload.global_config else None,
            library_config=payload.library_config.model_dump() if payload.library_config else None,
            session_config=payload.session_config.model_dump() if payload.session_config else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "success": True,
        "message": "Model configuration updated.",
        "config": model_config,
    }


@app.post("/api/libraries")
def create_library(payload: CreateLibraryRequest) -> dict[str, object]:
    """Create a new library."""
    try:
        library = container.library_sync_service.create_library(
            name=payload.name,
            description=payload.description,
            folder_path=payload.folder_path,
            embedding_model=payload.embedding_model,
            embedding_max_input_tokens=payload.embedding_max_input_tokens,
            chunk_mode=payload.chunk_mode,
        )
        container.config_service.update_default_library_index_config(
            embedding_model=payload.embedding_model,
            embedding_max_input_tokens=payload.embedding_max_input_tokens,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "library": library}


@app.get("/api/libraries/{library_id}")
def get_library(library_id: int) -> dict[str, object]:
    """Return one library."""
    try:
        library = container.library_sync_service.get_library(library_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"library": library}


@app.patch("/api/libraries/{library_id}")
def update_library(library_id: int, payload: UpdateLibraryRequest) -> dict[str, object]:
    """Update one library."""
    try:
        library = container.library_sync_service.update_library(
            library_id,
            name=payload.name,
            description=payload.description,
            folder_path=payload.folder_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "library": library}


@app.post("/api/libraries/{library_id}/configure-folder")
def configure_library_folder(library_id: int, payload: ConfigureFolderRequest) -> dict[str, object]:
    """Bind a local folder to one library."""
    if not payload.folder_path:
        raise HTTPException(status_code=400, detail="folder_path is required.")

    try:
        library = container.library_sync_service.configure_folder(library_id, payload.folder_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_count = len(list(Path(library["folder_path"]).rglob("*.pdf")))
    return {
        "success": True,
        "message": f"Configured folder for library '{library['name']}'.",
        "library": library,
        "paper_folder": library["folder_path"],
        "pdf_count": pdf_count,
    }


# @app.post("/api/libraries/{library_id}/sync")
# def sync_library(library_id: int, payload: ConfigureFolderRequest | None = None) -> dict[str, object]:
#     """Run an incremental sync for one library."""
#     folder_path = payload.folder_path if payload else None
#     try:
#         sync_result = container.library_sync_service.sync_library(
#             library_id,
#             folder_path=folder_path,
#             job_type="incremental",
#         )
#     except (FileNotFoundError, ValueError) as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc

#     return {
#         "success": True,
#         "message": f"Synchronized {sync_result['file_count']} PDF files into the library.",
#         **sync_result,
#     }


@app.post("/api/libraries/{library_id}/sync/start")
def start_sync_library(library_id: int, payload: ConfigureFolderRequest | None = None) -> dict[str, object]:
    """Start one background sync job for a library and return its job status."""
    folder_path = payload.folder_path if payload else None
    try:
        job_status = container.library_sync_service.start_sync_job(
            library_id,
            folder_path=folder_path,
            job_type="incremental",
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "success": True,
        "message": "Sync job started.",
        **job_status,
    }


@app.get("/api/sync-jobs/{job_id}")
def get_sync_job(job_id: int) -> dict[str, object]:
    """Return one sync job status for polling the background worker."""
    try:
        job_status = container.library_sync_service.get_sync_job_status(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "success": True,
        "message": "Sync job status loaded.",
        **job_status,
    }


@app.get("/api/libraries/{library_id}/documents")
def get_library_documents(library_id: int) -> dict[str, object]:
    """Return one library and the titles/update times of all its documents."""
    try:
        return container.library_sync_service.get_library_details(library_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/libraries/{library_id}/documents/{document_id}")
def get_library_document_details(library_id: int, document_id: int) -> dict[str, object]:
    """Return the metadata details for one library document."""
    try:
        return container.library_sync_service.get_document_details(library_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/libraries/{library_id}/documents/{document_id}")
def delete_library_document(library_id: int, document_id: int) -> dict[str, object]:
    """Delete one document from a library and remove its vector index."""
    try:
        container.library_sync_service.delete_document(library_id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "library_id": library_id, "document_id": document_id}


@app.delete("/api/libraries/{library_id}")
def delete_library(library_id: int) -> dict[str, object]:
    """Delete one library when it is no longer referenced by any session."""
    try:
        container.library_sync_service.delete_library(library_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 409
        raise HTTPException(status_code=status_code, detail=message) from exc
    return {"success": True, "library_id": library_id}



@app.get("/api/sessions")
def list_sessions() -> dict[str, object]:
    """List all chat sessions."""
    sessions = [session.__dict__ for session in container.chat_service.list_sessions()]
    return {"sessions": sessions}


@app.post("/api/sessions")
def create_session(payload: CreateSessionRequest) -> dict[str, object]:
    """Create a new chat session."""
    try:
        session = container.chat_service.create_session(
            title=payload.title,
            user_goal=payload.user_goal,
            library_id=payload.library_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "session": session.__dict__}


@app.patch("/api/sessions/{session_id}")
def rename_session(session_id: int, payload: UpdateSessionRequest) -> dict[str, object]:
    """Update one session title, pin status or one-time library binding."""
    try:
        session = None
        if payload.title is not None:
            session = container.chat_service.rename_session(session_id, payload.title)
        if payload.is_pinned is not None:
            session = container.chat_service.set_session_pinned(session_id, payload.is_pinned)
        if payload.library_id is not None:
            session = container.chat_service.bind_session_library(session_id, payload.library_id)
        if session is None:
            raise HTTPException(status_code=400, detail="Please provide title, is_pinned or library_id.")
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {"success": True, "session": session.__dict__}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int) -> dict[str, object]:
    """Delete one session."""
    try:
        container.chat_service.delete_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "session_id": session_id}


@app.get("/api/sessions/{session_id}/messages")
def list_session_messages(session_id: int) -> dict[str, object]:
    """Return the full message history for one session."""
    messages = [message.__dict__ for message in container.chat_service.list_messages(session_id)]
    return {"session_id": session_id, "messages": messages}

@app.post("/api/sessions/{session_id}/chat/stream")
def stream_chat_with_session(session_id: int, payload: ChatRequest) -> StreamingResponse:
    """Handle one streaming chat turn."""

    async def event_generator():
        try:
            for event in container.chat_service.stream_chat(
                session_id=session_id,
                user_message=payload.message,
                top_k=payload.top_k,
                allow_external_search=payload.allow_external_search,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
        except ValueError as exc:
            error_event = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("UPLOAD_API_HOST", "127.0.0.1")
    port = int(os.getenv("UPLOAD_API_PORT", "8000"))
    reload_enabled = os.getenv("UPLOAD_API_RELOAD", "1") == "1"
    app_target = "upload_api:app" if reload_enabled else app
    uvicorn.run(app_target, host=host, port=port, reload=reload_enabled)
