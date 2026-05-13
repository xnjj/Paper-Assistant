from __future__ import annotations

from datetime import datetime

from app_backend.db.connection import DatabaseManager


class SyncRepository:
    """同步任务仓储。"""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_job(self, folder_path: str, job_type: str) -> int:
        """创建同步任务记录并返回任务 id。"""
        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO library_sync_jobs(
                    folder_path, job_type, status, scanned_count,
                    new_count, skipped_count, failed_count,
                    error_message, started_at, finished_at
                )
                VALUES(?, ?, 'running', 0, 0, 0, 0, '', ?, NULL)
                """,
                (folder_path, job_type, now),
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
        """记录同步任务中的单文件处理结果。"""
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
        """结束同步任务并更新统计信息。"""
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
