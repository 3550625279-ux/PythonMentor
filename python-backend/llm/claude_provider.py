import anthropic
from .provider import LLMProvider

class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", base_url: str = ""):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.model = model

    async def chat_stream(self, messages, system, temperature=0.7, max_tokens=2048):
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat(self, messages, system, temperature=0.7, max_tokens=2048):
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        if not response.content:
            return ""
        # 优先返回 TextBlock，不泄露 ThinkingBlock
        for block in response.content:
            if block.type == "text":
                return block.text
        # 没有 TextBlock 时返回空字符串（不泄露 thinking 内容）
        return ""
