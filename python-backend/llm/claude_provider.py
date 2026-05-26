import anthropic
from .provider import LLMProvider

class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", base_url: str = ""):
        super().__init__()
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.model = model

    async def chat_stream(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=m,
            temperature=t,
            top_p=p,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=m,
            temperature=t,
            top_p=p,
            system=system,
            messages=messages,
        )
        if not response.content:
            return ""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
