from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    """所有 LLM provider 的统一接口。"""

    def __init__(self):
        from config import settings
        self.default_temperature = settings.temperature
        self.default_max_tokens = settings.max_tokens
        self.default_top_p = settings.top_p

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> AsyncIterator[str]:
        """流式对话，逐 token yield。"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> str:
        """非流式对话，返回完整文本。"""
        ...

    def _resolve_params(self, temperature, max_tokens, top_p) -> tuple[float, int, float]:
        """将 None 参数解析为配置默认值。"""
        t = temperature if temperature is not None else self.default_temperature
        m = max_tokens if max_tokens is not None else self.default_max_tokens
        p = top_p if top_p is not None else self.default_top_p
        return t, m, p
