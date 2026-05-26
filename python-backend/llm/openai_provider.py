import openai
from .provider import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = ""):
        super().__init__()
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.AsyncOpenAI(**kwargs)
        self.model = model

    def _build_messages(self, messages, system):
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.extend(messages)
        return result

    async def chat_stream(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=m,
            temperature=t,
            top_p=p,
            messages=self._build_messages(messages, system),
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=m,
            temperature=t,
            top_p=p,
            messages=self._build_messages(messages, system),
        )
        return response.choices[0].message.content or "" if response.choices else ""
