"""RAG 模块 — 提供共享的 retriever 单例。"""

import logging
from rag.retriever import HybridRetriever
from config import settings

logger = logging.getLogger(__name__)

_retriever: HybridRetriever | None = None
_init_attempted = False


def get_retriever() -> HybridRetriever | None:
    """返回共享的 HybridRetriever 单例。

    如果 embedding API key 未配置，返回 None（优雅降级，不阻断聊天）。
    """
    global _retriever, _init_attempted
    if _retriever is not None:
        return _retriever
    if _init_attempted:
        return None

    if not settings.embedding_api_key:
        logger.warning("Embedding API key 未配置，RAG 检索不可用")
        _init_attempted = True
        return None

    try:
        _retriever = HybridRetriever(
            db_path=settings.chroma_db_path,
            distance_threshold=settings.distance_threshold,
            api_key=settings.embedding_api_key,
            api_model=settings.embedding_api_model,
            api_url=settings.embedding_api_url,
            dimensions=settings.embedding_dimensions,
        )
        _init_attempted = True
        return _retriever
    except Exception as e:
        logger.warning("RAG retriever 初始化失败: %s", e)
        _init_attempted = True
        return None
