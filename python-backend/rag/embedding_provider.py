"""统一嵌入提供模块。

支持阿里云 DashScope API 和本地 sentence-transformers。
提供与 SentenceTransformer 兼容的 encode() 接口。
"""

import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """嵌入提供者抽象基类。"""

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """将文本列表编码为向量列表。"""
        ...


class DashScopeEmbedding(EmbeddingProvider):
    """阿里云 DashScope 嵌入 API。"""

    def __init__(self, api_key: str, model: str = "text-embedding-v4",
                 base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
                 dimensions: int = 1024):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dimensions = dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        """调用 DashScope API 批量生成嵌入向量。"""
        if not texts:
            return []

        # API 每次最多处理 10 条，分批
        all_embeddings = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self._call_api(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """单次 API 调用。"""
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": texts,
                "parameters": {"dimensions": self.dimensions},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # 按 index 排序，保证顺序与输入一致
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]


class SentenceTransformerEmbedding(EmbeddingProvider):
    """本地 sentence-transformers 模型（fallback）。"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()


def create_embedding_provider(
    api_key: str = "",
    model: str = "text-embedding-v4",
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    dimensions: int = 1024,
    fallback_model: str = "all-MiniLM-L6-v2",
) -> EmbeddingProvider:
    """根据配置创建嵌入提供者。

    有 API key 时用 DashScope，否则 fallback 到本地模型。
    """
    if api_key:
        logger.info("使用 DashScope 嵌入模型: %s (dim=%d)", model, dimensions)
        return DashScopeEmbedding(
            api_key=api_key,
            model=model,
            base_url=base_url,
            dimensions=dimensions,
        )
    else:
        logger.info("未配置嵌入 API key，使用本地模型: %s", fallback_model)
        return SentenceTransformerEmbedding(fallback_model)
