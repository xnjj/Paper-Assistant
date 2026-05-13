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

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    authors_json TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    doi TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    content_text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    vector_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(document_id, chunk_index),
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS library_sync_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    scanned_count INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT
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
    title TEXT NOT NULL,
    user_goal TEXT NOT NULL,
    is_pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
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
    """SQLite 连接管理器。

    这层只负责建表和提供连接，不承载业务逻辑。
    """

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or config.APP_DB_FILE
        config.ensure_runtime_directories()
        self.initialize()

    def initialize(self) -> None:
        """初始化数据库表结构。"""
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(SCHEMA_SQL)
            self._migrate_schema(connection)
            connection.commit()

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        """涓哄凡鏈夋暟鎹簱琛ヨ冻鏂板瀛楁銆?"""
        session_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(chat_sessions)").fetchall()
        }
        if "is_pinned" not in session_columns:
            connection.execute(
                "ALTER TABLE chat_sessions ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0"
            )

    @contextmanager
    def get_connection(self):
        """返回启用 Row 工厂的数据库连接。"""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
