from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


def _int_env(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _float_env(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


class Settings(BaseModel):
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", ""))
    serp_api_key: str = Field(default=os.getenv("SERP_API_KEY", ""))
    whatsapp_verify_token: str = Field(default=os.getenv("WHATSAPP_VERIFY_TOKEN", ""))
    whatsapp_access_token: str = Field(default=os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    whatsapp_phone_number_id: str = Field(
        default=os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    )
    google_client_id: str = Field(default=os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = Field(default=os.getenv("GOOGLE_CLIENT_SECRET", ""))
    google_redirect_base_url: str = Field(default=os.getenv("GOOGLE_REDIRECT_BASE_URL", ""))
    port: int = Field(default=_int_env("PORT", 8000))
    openai_model: str = Field(default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    openai_small_model: str = Field(default=os.getenv("OPENAI_SMALL_MODEL", "gpt-4.1-nano"))
    openai_timeout_seconds: float = Field(default=_float_env("OPENAI_TIMEOUT_SECONDS", 20.0))
    full_mode_max_tokens: int = Field(default=_int_env("FULL_MODE_MAX_TOKENS", 260))
    execute_mode_max_tokens: int = Field(default=_int_env("EXECUTE_MODE_MAX_TOKENS", 180))
    classify_max_tokens: int = Field(default=_int_env("CLASSIFY_MAX_TOKENS", 80))
    planning_max_tokens: int = Field(default=_int_env("PLANNING_MAX_TOKENS", 220))
    execution_parse_max_tokens: int = Field(default=_int_env("EXECUTION_PARSE_MAX_TOKENS", 160))
    serp_cache_ttl_seconds: int = Field(default=_int_env("SERP_CACHE_TTL_SECONDS", 86400))
    serp_cache_max_size: int = Field(default=_int_env("SERP_CACHE_MAX_SIZE", 256))
    playwright_timeout_ms: int = Field(default=_int_env("PLAYWRIGHT_TIMEOUT_MS", 15000))
    google_scopes: list[str] = Field(
        default=["https://www.googleapis.com/auth/calendar.events"]
    )
    token_storage_dir: str = Field(default=os.getenv("TOKEN_STORAGE_DIR", "/data"))
    graph_api_version: str = Field(default=os.getenv("WHATSAPP_API_VERSION", "v21.0"))

    @property
    def google_redirect_uri(self) -> str:
        base = self.google_redirect_base_url.rstrip("/")
        if not base:
            return ""
        return f"{base}/auth/google/callback"

    @property
    def token_file_path(self) -> Path | None:
        storage_dir = Path(self.token_storage_dir)
        if storage_dir.exists() and storage_dir.is_dir():
            return storage_dir / "google_token.enc"
        return None

    @property
    def token_encryption_key(self) -> bytes:
        seed = f"{self.google_client_id}:{self.google_client_secret}".encode("utf-8")
        digest = hashlib.sha256(seed).digest()
        return base64.urlsafe_b64encode(digest)


settings = Settings()

