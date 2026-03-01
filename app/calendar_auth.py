from __future__ import annotations

from google.oauth2.credentials import Credentials

from app.config import settings


def get_google_credentials() -> Credentials:
    if not (
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_refresh_token
    ):
        raise ValueError("Google Calendar credentials are not fully configured.")

    return Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )

