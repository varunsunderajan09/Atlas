from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    whatsapp_verify_token: str = Field(default=os.getenv("WHATSAPP_VERIFY_TOKEN", ""))
    whatsapp_access_token: str = Field(default=os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", ""))
    serp_api_key: str = Field(default=os.getenv("SERP_API_KEY", ""))
    google_client_id: str = Field(default=os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = Field(default=os.getenv("GOOGLE_CLIENT_SECRET", ""))
    agent_name: str = Field(default=os.getenv("AGENT_NAME", "Atlas"))
    port: int = Field(default=int(os.getenv("PORT", "8000")))
    openai_model: str = Field(default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    openai_classifier_model: str = Field(
        default=os.getenv("OPENAI_CLASSIFIER_MODEL", "gpt-4.1-nano")
    )
    openai_timeout_seconds: float = Field(
        default=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
    )
    serp_cache_ttl_seconds: int = Field(default=int(os.getenv("SERP_CACHE_TTL_SECONDS", "900")))
    playwright_timeout_ms: int = Field(default=int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "15000")))
    max_tool_results: int = Field(default=int(os.getenv("MAX_TOOL_RESULTS", "5")))
    final_response_max_tokens: int = Field(default=int(os.getenv("FINAL_RESPONSE_MAX_TOKENS", "220")))
    classifier_max_tokens: int = Field(default=int(os.getenv("CLASSIFIER_MAX_TOKENS", "80")))
    planning_max_tokens: int = Field(default=int(os.getenv("PLANNING_MAX_TOKENS", "180")))
    google_redirect_uri: str = Field(
        default=os.getenv("GOOGLE_REDIRECT_URI", "urn:ietf:wg:oauth:2.0:oob")
    )
    google_refresh_token: str = Field(default=os.getenv("GOOGLE_REFRESH_TOKEN", ""))
    calendar_id: str = Field(default=os.getenv("GOOGLE_CALENDAR_ID", "primary"))
    whatsapp_api_version: str = Field(default=os.getenv("WHATSAPP_API_VERSION", "v21.0"))


settings = Settings()

