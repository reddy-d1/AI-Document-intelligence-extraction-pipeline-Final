import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Document Intelligence & Extraction Pipeline"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./doc_intelligence.db")

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage"))

    # OCR Engine
    OCR_PROVIDER: str = "tesseract"

    # Anthropic API Key
    ANTHROPIC_API_KEY: str = ""

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "*",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

