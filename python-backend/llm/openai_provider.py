import openai
from .provider import LLMProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    def _build_messages(self, messages, system):
        """将 system prompt 注入消息列表（OpenAI API 不接受顶层 system 参数）。"""
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.extend(messages)
        return result

    async def chat_stream(self, messages, system, temperature=0.7, max_tokens=2048):
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=self._build_messages(messages, system),
            stream=True,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat(self, messages, system, temperature=0.7, max_tokens=2048):
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=self._build_messages(messages, system),
        )
        return response.choices[0].message.content or "" if response.choices else ""
