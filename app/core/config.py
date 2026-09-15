from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str
    PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8080"
    DATABASE_URL: str = "sqlite:///./db.sqlite3"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache
def get_settings():
    return Settings()
