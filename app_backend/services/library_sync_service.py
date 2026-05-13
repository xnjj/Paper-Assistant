from __future__ import annotations

from pathlib import Path

from app_backend.repositories.config_repository import ConfigRepository
from app_backend.repositories.sync_repository import SyncRepository
from app_backend.services.document_ingest_service import DocumentIngestService


class LibrarySyncService:
    """本地文献库同步服务。

    设计目标：
    - 新会话不重建全部索引，只复用已有持久化向量库。
    - 同步时依据文件哈希增量入库，只把新文档加入索引。
    """

    def __init__(
        self,
        ingest_service: DocumentIngestService,
        sync_repository: SyncRepository,
        config_repository: ConfigRepository,
    ) -> None:
        """初始化同步服务。

        Args:
            ingest_service: 文献入库编排服务。
            sync_repository: 同步任务记录仓储。
            config_repository: 应用配置仓储。
        """
        self.ingest_service = ingest_service
        self.sync_repository = sync_repository
        self.config_repository = config_repository

    def configure_folder(self, folder_path: str) -> str:
        """保存当前配置的文献目录。

        Args:
            folder_path: 用户在桌面端选择的本地文件夹路径。

        Returns:
            str: 规范化后的绝对路径。
        """
        path = Path(folder_path).resolve()
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"文献目录不存在: {path}")

        normalized_path = str(path)
        self.config_repository.set_value("paper_folder", normalized_path)
        return normalized_path

    def get_configured_folder(self) -> str | None:
        """读取当前配置的文献目录。"""
        return self.config_repository.get_value("paper_folder")

    def sync_folder(self, folder_path: str, job_type: str = "incremental") -> dict:
        """同步指定目录中的 PDF 文献。

        Args:
            folder_path: 待同步目录。
            job_type: 同步模式，当前支持 `incremental` 和后续可扩展的 `full`。

        Returns:
            dict: 同步任务摘要和逐文件处理结果。
        """
        normalized_path = self.configure_folder(folder_path)
        pdf_paths = sorted(str(path.resolve()) for path in Path(normalized_path).rglob("*.pdf"))
        if not pdf_paths:
            raise FileNotFoundError("配置的文献目录中没有 PDF 文件。")

        job_id = self.sync_repository.create_job(normalized_path, job_type)
        results = self.ingest_service.ingest_paths(pdf_paths, source_type="local_folder")

        new_count = 0
        skipped_count = 0
        failed_count = 0
        for result in results:
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

        return {
            "job_id": job_id,
            "paper_folder": normalized_path,
            "file_count": len(pdf_paths),
            "new_count": new_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "results": [result.__dict__ for result in results],
        }
