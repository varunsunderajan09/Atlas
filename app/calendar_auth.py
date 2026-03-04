from __future__ import annotations

import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings


logger = logging.getLogger(__name__)
_memory_token: dict[str, Any] | None = None


def _fernet() -> Fernet:
    return Fernet(settings.token_encryption_key)


def build_flow(state: str | None = None) -> Flow:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri],
            }
        },
        scopes=settings.google_scopes,
        state=state,
    )
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def save_token(token_json: dict[str, Any]) -> None:
    global _memory_token
    token_path = settings.token_file_path
    encrypted = _fernet().encrypt(json.dumps(token_json).encode("utf-8"))
    if token_path is not None:
        token_path.write_bytes(encrypted)
        return
    _memory_token = token_json
    logger.warning("No writable token volume detected. Using in-memory token storage.")


def load_token() -> dict[str, Any] | None:
    token_path = settings.token_file_path
    if token_path is not None and token_path.exists():
        try:
            payload = _fernet().decrypt(token_path.read_bytes())
            return json.loads(payload.decode("utf-8"))
        except (InvalidToken, json.JSONDecodeError) as exc:
            logger.error("Failed to load encrypted Google token: %s", exc)
            return None
    return _memory_token


def get_google_credentials() -> Credentials:
    token = load_token()
    if token is None:
        raise ValueError("Google Calendar is not authenticated.")

    credentials = Credentials.from_authorized_user_info(token, settings.google_scopes)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_token(json.loads(credentials.to_json()))
    return credentials

