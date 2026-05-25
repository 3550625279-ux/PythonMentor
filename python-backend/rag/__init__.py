"""RAG 模块 — 提供共享的 retriever 单例。"""

from rag.retriever import HybridRetriever
from config import settings

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """返回共享的 HybridRetriever 单例。"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(
            db_path=settings.chroma_db_path,
            model_name=settings.embedding_model,
            distance_threshold=settings.distance_threshold,
            api_key=settings.embedding_api_key,
            api_model=settings.embedding_api_model,
            api_url=settings.embedding_api_url,
            dimensions=settings.embedding_dimensions,
        )
    return _retriever
