from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from google import genai

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str | None = None
    PORT: int = 8000
    DATABASE_SQLITE_URL: str = "vendas_fake.db"
    # BACKEND_URL: str = "http://localhost:8080"
    # DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

@lru_cache
def get_settings():
    return Settings()

def get_gemini_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)