from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置"""

    APP_NAME: str = "Quant_Morrisony"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 默认测试股票（AkShare 格式：纯数字代码）
    DEFAULT_STOCK_CODE: str = "600519"

    # 数据缓存（秒）
    DATA_CACHE_TTL: int = 300

    # ─── RAG 知识库配置 ───
    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Embedding 配置 (使用 OpenAI 兼容接口)
    EMBEDDING_API_KEY: str = ""  # 若为空则使用 DEEPSEEK_API_KEY
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # ChromaDB 配置
    CHROMA_PATH: str = "data/chroma"
    CHROMA_COLLECTION: str = "quant_knowledge"

    # RAG 参数
    RAG_TOP_K: int = 3
    RAG_MAX_CONTEXT_LENGTH: int = 4000
    RAG_CONFIDENCE_THRESHOLD: float = 0.5

    # 知识库文档路径（相对于项目根目录）
    KNOWLEDGE_PATH: str = "docs/knowledge"

    class Config:
        env_file = ".env"


settings = Settings()
