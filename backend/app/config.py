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

    class Config:
        env_file = ".env"


settings = Settings()
