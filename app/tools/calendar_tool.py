from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from googleapiclient.discovery import build

from app.calendar_auth import get_google_credentials
from app.config import settings


class GoogleCalendarTool:
    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        credentials = get_google_credentials()
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

        start_dt = self._parse_datetime(request.get("start"))
        end_dt = self._parse_datetime(request.get("end")) or (start_dt + timedelta(hours=1))

        event = {
            "summary": request.get("title", "Atlas Event"),
            "description": request.get("description", ""),
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        }

        if request.get("location"):
            event["location"] = request["location"]

        created = (
            service.events()
            .insert(calendarId=settings.calendar_id, body=event)
            .execute()
        )

        return {
            "id": created.get("id", ""),
            "title": created.get("summary", ""),
            "start": created.get("start", {}).get("dateTime", ""),
            "link": created.get("htmlLink", ""),
        }

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc) + timedelta(hours=1)
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

