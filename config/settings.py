from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = ""
    DB_URL: str = "sqlite:///./tongkehui.db"
    LOCAL_FALLBACK_DB_URL: str = "sqlite:///./tongkehui.db"
    DB_AUTO_FALLBACK: bool = True
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:5177,*"
    DEBUG: bool = True
    
    # LLM settings
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-3.5-turbo"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VISION_MODEL: str = "gpt-4o"
    DEEPSEARCH_API_KEY: str = ""
    DEEPSEARCH_API_BASE: str = ""
    DEEPSEARCH_MODEL: str = ""
    DEEPSEARCH_ENABLE_SEARCH: bool = True
    DEEPSEARCH_SELF_CHECK: bool = True

    # Volcengine image generation settings
    VOLCENGINE_API_KEY: str = "73e088d0-f63d-4c21-a386-3a8f46f28cd2"
    VOLCENGINE_IMAGE_MODEL: str = "doubao-seedream-5-0-260128"

    # SerpAPI (谷歌学术) settings
    SERPAPI_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

    @property
    def database_url(self) -> str:
        return (self.DATABASE_URL or self.DB_URL).strip()

    class Config:
        env_file = ".env"

settings = Settings()
