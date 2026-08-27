import os
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

# backend/ directory (where .env lives)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    GOOGLE_DRIVE_FOLDER_ID: str
    GOOGLE_SERVICE_ACCOUNT_FILE: str
    FRONTEND_URL: str = "http://localhost:3000"
    SEARCH_RESULT_LIMIT: int = 20
    MAX_SNIPPETS_PER_FILE: int = 3
    CACHE_TTL_SECONDS: int = 300
    CACHE_MAX_SIZE: int = 100
    SNIPPET_CONTEXT_CHARS: int = 150
    ALLOWED_MIME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    ]

    @model_validator(mode="after")
    def resolve_sa_file_path(self) -> "Settings":
        p = Path(self.GOOGLE_SERVICE_ACCOUNT_FILE)
        if not p.is_absolute():
            # resolve relative to the backend/ directory
            resolved = (_BACKEND_DIR / p).resolve()
            self.GOOGLE_SERVICE_ACCOUNT_FILE = str(resolved)
        return self

    model_config = {
        "env_file": str(_BACKEND_DIR / ".env"),
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()