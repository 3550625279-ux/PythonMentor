"""RAG 混合检索器。

结合向量相似度检索和元数据过滤，
从 collection_knowledge 和 collection_history 两个集合中检索，
根据查询内容和错误类型返回最相关的知识片段。

用法：
    retriever = HybridRetriever(db_path="../chroma_db")
    results = retriever.retrieve("TypeError unsupported operand", error_type="TypeError")
"""

import logging

import chromadb
from rag.embedding_provider import create_embedding_provider

logger = logging.getLogger(__name__)


class HybridRetriever:
    """混合检索器：双 collection 向量检索 + 距离阈值过滤 + 来源标签。

    工作流程：
    1. 用 sentence-transformers 将查询编码为向量
    2. 分别在 collection_knowledge 和 collection_history 中检索
    3. 合并结果，按距离阈值过滤低相关性结果
    4. 如果指定了 error_type，将同类型文档排在前面
    5. 每条结果标记来源（knowledge / history）
    6. 返回 top_k 条结果
    """

    def __init__(
        self,
        db_path: str,
        distance_threshold: float = 0.7,
        api_key: str = "",
        api_model: str = "text-embedding-v4",
        api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        dimensions: int = 1024,
    ):
        """初始化检索器。

        Args:
            db_path: ChromaDB 持久化存储路径
            distance_threshold: 距离阈值，超过此值的结果将被过滤（cosine distance）
            api_key: Embedding API key（必需）
            api_model: Embedding 模型名
            api_url: Embedding API 地址
            dimensions: 嵌入维度
        """
        self.embedder = create_embedding_provider(
            api_key=api_key, model=api_model, base_url=api_url,
            dimensions=dimensions,
        )
        self.distance_threshold = distance_threshold
        client = chromadb.PersistentClient(path=db_path)

        # 加载两个 collection
        self.knowledge_collection = client.get_or_create_collection(
            "collection_knowledge",
            metadata={"hnsw:space": "cosine"},
        )
        self.history_collection = client.get_or_create_collection(
            "collection_history",
            metadata={"hnsw:space": "cosine"},
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        error_type: str | None = None,
    ) -> list[dict]:
        """从两个 collection 中检索与查询最相关的知识片段。

        Args:
            query: 用户查询文本（可以是报错信息、问题描述等）
            top_k: 返回结果数量
            error_type: 可选的错误类型过滤（如 "TypeError"），
                        同类型的文档会被优先返回

        Returns:
            包含 id、text、metadata、distance、source 的字典列表
        """
        query_embedding = self.embedder.encode([query])
        all_docs = []

        # 1. 检索 collection_knowledge
        kb_results = self.knowledge_collection.query(
            query_embeddings=query_embedding,
            n_results=top_k * 2,
        )
        for i in range(len(kb_results["ids"][0])):
            doc = {
                "id": kb_results["ids"][0][i],
                "text": kb_results["documents"][0][i],
                "metadata": kb_results["metadatas"][0][i],
                "distance": kb_results["distances"][0][i] if kb_results["distances"] else 0,
                "source": "knowledge",
            }
            all_docs.append(doc)

        # 2. 检索 collection_history（仅当有文档时）
        history_count = self.history_collection.count()
        if history_count > 0:
            try:
                hist_results = self.history_collection.query(
                    query_embeddings=query_embedding,
                    n_results=min(top_k, history_count),
                )
                for i in range(len(hist_results["ids"][0])):
                    doc = {
                        "id": hist_results["ids"][0][i],
                        "text": hist_results["documents"][0][i],
                        "metadata": hist_results["metadatas"][0][i],
                        "distance": hist_results["distances"][0][i] if hist_results["distances"] else 0,
                        "source": "history",
                    }
                    all_docs.append(doc)
            except Exception as e:
                logger.warning("history collection 检索失败: %s", e)

        # 3. 距离阈值过滤
        filtered = [d for d in all_docs if d["distance"] <= self.distance_threshold]

        # 如果过滤后没有结果，保留知识库中距离最近的 1 条
        if not filtered:
            logger.info("所有结果距离超过阈值 %.2f，保留最近的 1 条", self.distance_threshold)
            kb_only = [d for d in all_docs if d["source"] == "knowledge"]
            filtered = sorted(kb_only, key=lambda d: d["distance"])[:1]

        # 4. 错误类型增强排序
        if error_type:
            same_type = [d for d in filtered if d["metadata"].get("error_type") == error_type]
            other_type = [d for d in filtered if d["metadata"].get("error_type") != error_type]
            filtered = same_type + other_type

        return filtered[:top_k]

    def get_collection_stats(self) -> dict:
        """返回知识库统计信息。"""
        return {
            "knowledge_count": self.knowledge_collection.count(),
            "history_count": self.history_collection.count(),
        }
