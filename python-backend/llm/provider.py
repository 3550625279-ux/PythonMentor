from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    """所有 LLM provider 的统一接口。"""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """流式对话，逐 token yield。"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """非流式对话，返回完整文本。"""
        ...
