from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.agent import AtlasAgent
from app.config import settings


app = FastAPI(title="Atlas Assistant", version="1.0.0")
agent = AtlasAgent()


def extract_whatsapp_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                messages.append(
                    {
                        "from": message.get("from", ""),
                        "body": message.get("text", {}).get("body", "").strip(),
                        "phone_number_id": phone_number_id,
                    }
                )
    return messages


def strip_invocation(message: str) -> str | None:
    agent_name = settings.agent_name.strip() or "Atlas"
    prefix = f"@{agent_name}"
    if not message.lower().startswith(prefix.lower()):
        return None
    cleaned = message[len(prefix) :].strip()
    return cleaned or None


async def send_whatsapp_message(to: str, phone_number_id: str, body: str) -> None:
    if not (settings.whatsapp_access_token and phone_number_id and to and body):
        return

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body[:4000]},
    }
    async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse({"ok": True, "agent_name": settings.agent_name})


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> PlainTextResponse:
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook(request: Request) -> PlainTextResponse:
    payload = await request.json()
    for item in extract_whatsapp_messages(payload):
        cleaned = strip_invocation(item["body"])
        if not cleaned:
            continue
        response_text = await agent.handle(cleaned)
        await send_whatsapp_message(
            to=item["from"],
            phone_number_id=item["phone_number_id"],
            body=response_text,
        )
    return PlainTextResponse("OK")
