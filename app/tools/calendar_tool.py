from __future__ import annotations

from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from app.calendar_auth import get_google_credentials


class CalendarTool:
    def create_event(
        self,
        summary: str,
        start_dt: str | None,
        end_dt: str | None,
        location: str | None = None,
        description: str | None = None,
    ) -> dict:
        credentials = get_google_credentials()
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        start = self._parse_datetime(start_dt)
        end = self._parse_datetime(end_dt) if end_dt else start + timedelta(hours=1)
        body = {
            "summary": summary,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
            "location": location or "",
            "description": description or "",
        }
        event = service.events().insert(calendarId="primary", body=body).execute()
        return {
            "summary": event.get("summary", summary),
            "start": event.get("start", {}).get("dateTime", start.isoformat()),
            "link": event.get("htmlLink", ""),
        }

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

