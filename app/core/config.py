from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

ENV = get_settings()