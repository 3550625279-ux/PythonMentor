import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    # LLM 后端选择: "claude" | "openai" | "ollama"
    llm_backend: str = os.getenv("LLM_BACKEND", "ollama")

    # Claude 配置
    claude_api_key: str = os.getenv("CLAUDE_API_KEY", "")
    claude_base_url: str = os.getenv("CLAUDE_BASE_URL", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # OpenAI 配置
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Ollama 配置
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

    # 服务配置
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    dev_mode: bool = os.getenv("DEV_MODE", "false").lower() == "true"

    # RAG 配置
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    distance_threshold: float = float(os.getenv("DISTANCE_THRESHOLD", "0.7"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))

    # 嵌入 API 配置（DashScope）
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_api_model: str = os.getenv("EMBEDDING_API_MODEL", "text-embedding-v4")
    embedding_api_url: str = os.getenv("EMBEDDING_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_dimensions: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

    # 批评模型配置
    critique_enabled: bool = os.getenv("CRITIQUE_ENABLED", "false").lower() == "true"
    critique_model: str = os.getenv("CRITIQUE_MODEL", "")

settings = Settings()
