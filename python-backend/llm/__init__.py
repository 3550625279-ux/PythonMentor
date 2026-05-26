from config import settings
from .provider import LLMProvider
from .ollama_provider import OllamaProvider

_provider: LLMProvider | None = None

def get_provider() -> LLMProvider:
    """根据配置返回对应的 LLM provider（单例缓存）。"""
    global _provider
    if _provider is not None:
        return _provider

    if settings.llm_backend == "claude":
        from .claude_provider import ClaudeProvider
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY 未设置")
        _provider = ClaudeProvider(api_key=settings.claude_api_key, model=settings.claude_model, base_url=settings.claude_base_url)
    elif settings.llm_backend == "openai":
        from .openai_provider import OpenAIProvider
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未设置")
        _provider = OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model, base_url=settings.openai_base_url)
    elif settings.llm_backend == "ollama":
        _provider = OllamaProvider(base_url=settings.ollama_url, model=settings.ollama_model)
    else:
        raise ValueError(f"未知的 LLM 后端: {settings.llm_backend}")

    return _provider


_critique_provider: LLMProvider | None = None

def get_critique_provider() -> LLMProvider | None:
    """返回批评模型的 provider。如果未启用，返回 None。

    当 critique_model 为空时，复用主 provider（同一后端同一模型）。
    否则按 critique_model 指定的后端创建独立 provider。
    """
    global _critique_provider
    if not settings.critique_enabled:
        return None
    if _critique_provider is not None:
        return _critique_provider

    # 未指定独立批评模型 → 直接复用主 provider
    if not settings.critique_model:
        _critique_provider = get_provider()
        return _critique_provider

    try:
        # 按主后端类型创建，但使用 critique_model 指定的模型
        if settings.llm_backend == "claude":
            from .claude_provider import ClaudeProvider
            _critique_provider = ClaudeProvider(
                api_key=settings.claude_api_key,
                model=settings.critique_model,
                base_url=settings.claude_base_url,
            )
        elif settings.llm_backend == "openai":
            from .openai_provider import OpenAIProvider
            _critique_provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                model=settings.critique_model,
                base_url=settings.openai_base_url,
            )
        else:
            _critique_provider = OllamaProvider(
                base_url=settings.ollama_url,
                model=settings.critique_model,
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("批评模型初始化失败，跳过: %s", e)
        return None

    return _critique_provider
