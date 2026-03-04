from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


def extract_text_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                messages.append(
                    {
                        "from": message.get("from", ""),
                        "text": message.get("text", {}).get("body", "").strip(),
                    }
                )
    return messages


class WhatsAppClient:
    async def send_text(self, to_phone: str, text: str) -> None:
        if not (
            settings.whatsapp_access_token
            and settings.whatsapp_phone_number_id
            and to_phone
            and text
        ):
            logger.warning("WhatsApp send skipped due to missing config or payload.")
            return

        url = (
            f"https://graph.facebook.com/{settings.graph_api_version}/"
            f"{settings.whatsapp_phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": text[:4000]},
        }
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("WhatsApp send failed: %s", exc)

