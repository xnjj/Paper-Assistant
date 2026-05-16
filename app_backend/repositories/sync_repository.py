from __future__ import annotations

from datetime import datetime

from app_backend.db.connection import DatabaseManager


class SyncRepository:
    """Repository for library synchronization jobs."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_job(self, library_id: int, folder_path: str, job_type: str) -> int:
        """Create one sync job and return its primary key."""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO library_sync_jobs(
                    library_id, folder_path, job_type, status, scanned_count,
                    new_count, skipped_count, failed_count,
                    error_message, started_at, finished_at
                )
                VALUES(?, ?, ?, 'running', 0, 0, 0, 0, '', ?, NULL)
                """,
                (library_id, folder_path, job_type, now),
            )
            return int(cursor.lastrowid)

    def add_item(
        self,
        *,
        job_id: int,
        file_path: str,
        file_hash: str,
        document_id: int | None,
        status: str,
        message: str,
    ) -> None:
        """Record the result of one file inside a sync job."""
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO library_sync_items(job_id, file_path, file_hash, document_id, status, message)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (job_id, file_path, file_hash, document_id, status, message),
            )

    def finish_job(
        self,
        *,
        job_id: int,
        status: str,
        scanned_count: int,
        new_count: int,
        skipped_count: int,
        failed_count: int,
        error_message: str = "",
    ) -> None:
        """Mark one sync job as finished and write summary counts."""
        finished_at = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                UPDATE library_sync_jobs
                SET status = ?, scanned_count = ?, new_count = ?, skipped_count = ?,
                    failed_count = ?, error_message = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, scanned_count, new_count, skipped_count, failed_count, error_message, finished_at, job_id),
            )

    def get_job(self, job_id: int) -> dict | None:
        """Return one sync job row as a plain dictionary."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id, library_id, folder_path, job_type, status, scanned_count,
                    new_count, skipped_count, failed_count, error_message,
                    started_at, finished_at
                FROM library_sync_jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_items(self, job_id: int) -> list[dict]:
        """Return all recorded sync items for one job."""
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, job_id, file_path, file_hash, document_id, status, message
                FROM library_sync_items
                WHERE job_id = ?
                ORDER BY id ASC
                """,
                (job_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_items_for_document(self, document_id: int) -> None:
        """Delete sync item rows that reference one document."""
        with self.db_manager.get_connection() as connection:
            connection.execute(
                "DELETE FROM library_sync_items WHERE document_id = ?",
                (document_id,),
            )
