from __future__ import annotations

from app_backend.repositories.document_repository import DocumentRepository
from app_backend.services.vector_index_service import VectorIndexService


class RetrieverService:
    """文献检索服务。

    该服务负责把向量召回结果与结构化文献元数据组合起来，
    供后续 agent、会话记忆拼接和回答生成使用。
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        vector_index_service: VectorIndexService,
    ) -> None:
        """初始化检索服务。

        Args:
            document_repository: 结构化文献仓储，用于回表查询标题、摘要等信息。
            vector_index_service: 向量索引服务，用于执行相似度检索。
        """
        self.document_repository = document_repository
        self.vector_index_service = vector_index_service

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """在本地文献库中检索与输入最相关的文本片段。

        Args:
            query: 用户问题、研究主题或待补充论据的描述。
            top_k: 期望返回的结果条数。

        Returns:
            list[dict]: 每条结果同时包含 chunk 内容和所属文献信息。
        """
        vector_results = self.vector_index_service.vector_store.similarity_search(query, k=top_k)
        merged_results: list[dict] = []

        for item in vector_results:
            metadata = item.metadata or {}
            document_id = metadata.get("document_id")
            if document_id is None:
                continue

            document = self.document_repository.get_by_id(int(document_id))
            if document is None:
                continue

            merged_results.append(
                {
                    "document_id": document.id,
                    "title": document.title,
                    "abstract": document.abstract,
                    "file_path": document.file_path,
                    "chunk_index": metadata.get("chunk_index"),
                    "chunk_text": item.page_content,
                }
            )
        return merged_results
