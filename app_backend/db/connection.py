from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import config_data as config


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    folder_path TEXT NOT NULL DEFAULT '',
    collection_name TEXT NOT NULL UNIQUE,
    embedding_model TEXT NOT NULL DEFAULT 'text-embedding-v1',
    embedding_max_input_tokens INTEGER NOT NULL DEFAULT 2048,
    chunk_mode TEXT NOT NULL DEFAULT 'recursive',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    authors_json TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    year TEXT NOT NULL DEFAULT '',
    doi TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    venue TEXT NOT NULL DEFAULT '',
    citation_text_default TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    content_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(library_id, file_hash),
    FOREIGN KEY(library_id) REFERENCES libraries(id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    vector_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(document_id, chunk_index),
    FOREIGN KEY(library_id) REFERENCES libraries(id),
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS library_sync_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL,
    folder_path TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    scanned_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY(library_id) REFERENCES libraries(id)
);

CREATE TABLE IF NOT EXISTS library_sync_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    document_id INTEGER,
    status TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(job_id) REFERENCES library_sync_jobs(id),
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER,
    title TEXT NOT NULL,
    user_goal TEXT NOT NULL,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(library_id) REFERENCES libraries(id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    retrieval_context_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    session_id INTEGER,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
);
"""


class DatabaseManager:
    """SQLite connection manager used by repositories and services."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or config.APP_DB_FILE
        config.ensure_runtime_directories()
        self.initialize()

    def initialize(self) -> None:
        """Create tables and run lightweight migrations."""
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(SCHEMA_SQL)
            self._migrate_schema(connection)
            connection.commit()

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        """Bring older database files forward to the current schema."""
        self._ensure_library_columns(connection)
        migration_library_id = self._ensure_migration_library_if_needed(connection)
        self._migrate_documents(connection, migration_library_id)
        self._ensure_document_metadata_columns(connection)
        self._ensure_session_columns(connection, migration_library_id)
        self._ensure_session_library_nullable(connection)
        self._ensure_sync_job_columns(connection, migration_library_id)
        self._ensure_chunk_columns(connection, migration_library_id)

    def _ensure_library_columns(self, connection: sqlite3.Connection) -> None:
        """Add library-level index configuration columns to older databases."""
        library_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(libraries)").fetchall()
        }
        if "embedding_model" not in library_columns:
            connection.execute(
                "ALTER TABLE libraries ADD COLUMN embedding_model TEXT NOT NULL DEFAULT 'text-embedding-v1'"
            )
        if "embedding_max_input_tokens" not in library_columns:
            connection.execute(
                "ALTER TABLE libraries ADD COLUMN embedding_max_input_tokens INTEGER NOT NULL DEFAULT 2048"
            )
        if "chunk_mode" not in library_columns:
            connection.execute(
                "ALTER TABLE libraries ADD COLUMN chunk_mode TEXT NOT NULL DEFAULT 'recursive'"
            )

    def _ensure_migration_library_if_needed(self, connection: sqlite3.Connection) -> int | None:
        """Create one compatibility library only when legacy global data must be migrated.

        This is intentionally not a runtime default library. It exists only when an
        older database already contains global documents/sessions that need a
        library owner after schema migration.
        """
        existing_library = connection.execute(
            "SELECT id FROM libraries ORDER BY id ASC LIMIT 1"
        ).fetchone()
        if existing_library:
            return int(existing_library[0])

        legacy_documents_need_migration = self._table_has_column(connection, "documents", "library_id") is False and self._table_has_rows(connection, "documents")
        legacy_sessions_need_migration = self._table_has_column(connection, "chat_sessions", "library_id") is False and self._table_has_rows(connection, "chat_sessions")
        legacy_sync_jobs_need_migration = self._table_has_column(connection, "library_sync_jobs", "library_id") is False and self._table_has_rows(connection, "library_sync_jobs")
        legacy_chunks_need_migration = self._table_has_column(connection, "document_chunks", "library_id") is False and self._table_has_rows(connection, "document_chunks")

        if not any(
            [
                legacy_documents_need_migration,
                legacy_sessions_need_migration,
                legacy_sync_jobs_need_migration,
                legacy_chunks_need_migration,
            ]
        ):
            return None

        cursor = connection.execute(
            """
            INSERT INTO libraries(
                name, description, folder_path, collection_name, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                "迁移文献库",
                "用于承接旧版全局文献库数据的迁移库。",
                config.get_paper_folder(),
                config.DATABASE_TABLE,
            ),
        )
        return int(cursor.lastrowid)

    def _migrate_documents(self, connection: sqlite3.Connection, migration_library_id: int | None) -> None:
        """Rebuild the documents table if it still uses the old global schema."""
        document_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "library_id" in document_columns:
            return

        connection.execute(
            """
            CREATE TABLE documents_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                keywords_json TEXT NOT NULL,
                year TEXT NOT NULL DEFAULT '',
                doi TEXT NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                venue TEXT NOT NULL DEFAULT '',
                citation_text_default TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL,
                source_uri TEXT NOT NULL,
                content_text TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(library_id, file_hash),
                FOREIGN KEY(library_id) REFERENCES libraries(id)
            )
            """
        )
        if migration_library_id is not None:
            connection.execute(
                """
                INSERT INTO documents_new(
                    id, library_id, file_hash, file_path, file_name, title, abstract,
                    authors_json, keywords_json, year, doi, url, venue,
                    citation_text_default, source_type, source_uri, content_text,
                    status, created_at, updated_at
                )
                SELECT
                    id, ?, file_hash, file_path, file_name, title, abstract,
                    authors_json, keywords_json, '', doi, '', '', '',
                    source_type, source_uri, content_text, status, created_at, updated_at
                FROM documents
                """,
                (migration_library_id,),
            )
        connection.execute("DROP TABLE documents")
        connection.execute("ALTER TABLE documents_new RENAME TO documents")

    def _ensure_document_metadata_columns(self, connection: sqlite3.Connection) -> None:
        """Add newer structured metadata columns to historical document tables."""
        document_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "year" not in document_columns:
            connection.execute(
                "ALTER TABLE documents ADD COLUMN year TEXT NOT NULL DEFAULT ''"
            )
        if "url" not in document_columns:
            connection.execute(
                "ALTER TABLE documents ADD COLUMN url TEXT NOT NULL DEFAULT ''"
            )
        if "venue" not in document_columns:
            connection.execute(
                "ALTER TABLE documents ADD COLUMN venue TEXT NOT NULL DEFAULT ''"
            )
        if "citation_text_default" not in document_columns:
            connection.execute(
                "ALTER TABLE documents ADD COLUMN citation_text_default TEXT NOT NULL DEFAULT ''"
            )

    def _ensure_session_columns(self, connection: sqlite3.Connection, migration_library_id: int | None) -> None:
        """Add newer session columns to older databases."""
        session_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(chat_sessions)").fetchall()
        }

        if "is_pinned" not in session_columns:
            connection.execute(
                "ALTER TABLE chat_sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0"
            )

        if "library_id" not in session_columns:
            connection.execute(
                "ALTER TABLE chat_sessions ADD COLUMN library_id INTEGER NOT NULL DEFAULT 0"
            )
            if migration_library_id is not None:
                connection.execute(
                    "UPDATE chat_sessions SET library_id = ? WHERE library_id = 0",
                    (migration_library_id,),
                )

    def _ensure_session_library_nullable(self, connection: sqlite3.Connection) -> None:
        """允许会话不绑定文献库，必要时重建旧的 NOT NULL 会话表。"""
        session_columns = connection.execute("PRAGMA table_info(chat_sessions)").fetchall()
        library_column = next((row for row in session_columns if row[1] == "library_id"), None)
        if library_column is None or int(library_column[3]) == 0:
            return

        connection.execute(
            """
            CREATE TABLE chat_sessions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER,
                title TEXT NOT NULL,
                user_goal TEXT NOT NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(library_id) REFERENCES libraries(id)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO chat_sessions_new(
                id, library_id, title, user_goal, is_pinned, created_at, updated_at
            )
            SELECT id, library_id, title, user_goal, is_pinned, created_at, updated_at
            FROM chat_sessions
            """
        )
        connection.execute("DROP TABLE chat_sessions")
        connection.execute("ALTER TABLE chat_sessions_new RENAME TO chat_sessions")

    def _ensure_sync_job_columns(self, connection: sqlite3.Connection, migration_library_id: int | None) -> None:
        """Add library ownership to historical sync jobs."""
        job_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(library_sync_jobs)").fetchall()
        }
        if "library_id" not in job_columns:
            connection.execute(
                "ALTER TABLE library_sync_jobs ADD COLUMN library_id INTEGER NOT NULL DEFAULT 0"
            )
            if migration_library_id is not None:
                connection.execute(
                    "UPDATE library_sync_jobs SET library_id = ? WHERE library_id = 0",
                    (migration_library_id,),
                )

    def _ensure_chunk_columns(self, connection: sqlite3.Connection, migration_library_id: int | None) -> None:
        """Backfill chunk-level library ids for older databases."""
        chunk_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(document_chunks)").fetchall()
        }
        if "library_id" not in chunk_columns:
            connection.execute(
                "ALTER TABLE document_chunks ADD COLUMN library_id INTEGER NOT NULL DEFAULT 0"
            )

        if migration_library_id is not None:
            connection.execute(
                """
                UPDATE document_chunks
                SET library_id = COALESCE(
                    (SELECT library_id FROM documents WHERE documents.id = document_chunks.document_id),
                    ?
                )
                WHERE library_id = 0
                """,
                (migration_library_id,),
            )

    @staticmethod
    def _table_has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Return whether a table currently contains a specific column."""
        columns = {
            row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        return column_name in columns

    @staticmethod
    def _table_has_rows(connection: sqlite3.Connection, table_name: str) -> bool:
        """Return whether a table currently stores any rows."""
        row = connection.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
        return row is not None

    @contextmanager
    def get_connection(self):
        """Return a connection configured with sqlite Row mapping."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
