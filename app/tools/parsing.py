from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml


def strip_prefix(message: str) -> tuple[str | None, str | None]:
    text = message.strip()
    lower = text.lower()
    if lower.startswith("@atlas-full"):
        return "full", text[len("@atlas-full") :].strip()
    if lower.startswith("@atlas-execute"):
        return "execute", text[len("@atlas-execute") :].strip()
    return None, None


def wants_availability(text: str) -> bool:
    lower = text.lower()
    return "availability" in lower or "available" in lower or "open table" in lower


def wants_calendar(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in ("add to calendar", "schedule", "put on my calendar"))


def wants_booking_links(text: str) -> bool:
    lower = text.lower()
    return "booking link" in lower or "book" in lower or "reservation link" in lower


def wants_itinerary(text: str) -> bool:
    lower = text.lower()
    return "itinerary" in lower or "day 1" in lower or "plan my trip" in lower


def parse_execution_block(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    try:
        parsed = yaml.safe_load(stripped)
        if isinstance(parsed, dict):
            return parsed
    except yaml.YAMLError:
        return None
    return None


def infer_simple_execution(text: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    restaurant_match = re.search(r"(?:for|at)\s+([A-Za-z0-9 '&.-]+)", text)
    target = restaurant_match.group(1).strip() if restaurant_match else text.strip()
    return {
        "query": target,
        "check_availability": wants_availability(text),
        "create_booking_links": wants_booking_links(text) or not wants_calendar(text),
        "create_calendar_event": wants_calendar(text),
        "calendar": {
            "summary": target[:80] or "Atlas Event",
            "start_dt": (now + timedelta(hours=1)).isoformat(),
            "end_dt": (now + timedelta(hours=2)).isoformat(),
            "location": "",
            "description": text.strip(),
        },
    }

