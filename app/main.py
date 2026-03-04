from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from app.agent import AtlasAgent
from app.calendar_auth import build_flow, save_token
from app.config import settings
from app.logging_config import configure_logging
from app.whatsapp import WhatsAppClient, extract_text_messages


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Atlas Assistant", version="2.0.0")
agent = AtlasAgent()
whatsapp_client = WhatsAppClient()
oauth_states: set[str] = set()


@app.get("/healthz")
async def healthz() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "google_oauth_ready": bool(
                settings.google_client_id
                and settings.google_client_secret
                and settings.google_redirect_base_url
            ),
        }
    )


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
    for message in extract_text_messages(payload):
        mode, cleaned = agent.parse_invocation(message["text"])
        if not mode or not cleaned:
            continue
        response_text = await agent.handle(mode, cleaned)
        await whatsapp_client.send_text(message["from"], response_text)
    return PlainTextResponse("OK")


@app.get("/auth/google/start")
async def auth_google_start() -> RedirectResponse:
    if not settings.google_redirect_uri:
        raise HTTPException(status_code=500, detail="GOOGLE_REDIRECT_BASE_URL is not configured")
    state = secrets.token_urlsafe(24)
    oauth_states.add(state)
    flow = build_flow(state=state)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback")
async def auth_google_callback(code: str, state: str) -> PlainTextResponse:
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    oauth_states.discard(state)
    flow = build_flow(state=state)
    flow.fetch_token(code=code)
    save_token_json = flow.credentials.to_json()
    import json

    save_token(json.loads(save_token_json))
    logger.info("Google OAuth token stored.")
    return PlainTextResponse("Google Calendar connected.")

