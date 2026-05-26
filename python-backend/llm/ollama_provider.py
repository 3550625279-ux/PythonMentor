import json
import httpx
from .provider import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:14b"):
        super().__init__()
        self.base_url = base_url
        self.model = model

    async def chat_stream(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "stream": True,
                    "options": {
                        "temperature": t,
                        "num_predict": m,
                        "top_p": p,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]

    async def chat(self, messages, system, temperature=None, max_tokens=None, top_p=None):
        t, m, p = self._resolve_params(temperature, max_tokens, top_p)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}] + messages,
                    "stream": False,
                    "options": {
                        "temperature": t,
                        "num_predict": m,
                        "top_p": p,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
