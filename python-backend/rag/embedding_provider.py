"""统一嵌入提供模块。

支持阿里云 DashScope API 和 OpenAI 兼容 API。
提供 encode() 接口用于生成文本嵌入向量。
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


class OpenAICompatibleEmbedding(EmbeddingProvider):
    """OpenAI 兼容嵌入 API（支持 OpenAI、DeepSeek 等）。"""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small",
                 base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self._call_api(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]


def create_embedding_provider(
    api_key: str = "",
    model: str = "text-embedding-v4",
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    dimensions: int = 1024,
) -> EmbeddingProvider:
    """根据配置创建嵌入提供者。

    必须提供 API key，否则抛出 ValueError。
    根据 base_url 自动选择 DashScope 或 OpenAI 兼容模式。
    """
    if not api_key:
        raise ValueError(
            "Embedding API key is required. "
            "Set 'python-mentor.embeddingApiKey' in VS Code settings, "
            "or set EMBEDDING_API_KEY in .env."
        )

    if "dashscope" in base_url:
        logger.info("Using DashScope embedding: %s (dim=%d)", model, dimensions)
        return DashScopeEmbedding(
            api_key=api_key, model=model,
            base_url=base_url, dimensions=dimensions,
        )
    else:
        logger.info("Using OpenAI-compatible embedding: %s", model)
        return OpenAICompatibleEmbedding(
            api_key=api_key, model=model, base_url=base_url,
        )
