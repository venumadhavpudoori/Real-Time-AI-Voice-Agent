import os
import json
from typing import List, Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Real-Time AI Voice Agent"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_db"
    )
    SQLITE_FALLBACK_URL: str = "sqlite+aiosqlite:///./restaurant.db"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            clean_v = v.strip()
            if clean_v.startswith("[") and clean_v.endswith("]"):
                try:
                    return json.loads(clean_v)
                except Exception:
                    pass
            # Split comma-separated string
            return [origin.strip() for origin in clean_v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # AI Configuration (Optional OpenAI or Gemini)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Safety Guardrails
    ENABLE_SAFETY_GUARDRAILS: bool = True
    STRICT_ALLERGY_MODE: bool = True
    MAX_PARTY_SIZE: int = 12
    RESERVATION_WINDOW_DAYS: int = 30
    DEFAULT_RESERVATION_DURATION_MINS: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
