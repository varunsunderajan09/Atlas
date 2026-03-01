# Atlas Assistant

Atlas is a stateless WhatsApp-based executive AI assistant for Railway.

## Project Structure

```text
atlas-assistant/
  app/
    main.py
    agent.py
    config.py
    cache.py
    calendar_auth.py
    tools/
      research.py
      planning.py
      availability.py
      booking_links.py
      calendar_tool.py
  requirements.txt
  Dockerfile
  railway.json
  README.md
```

## Environment Variables

```env
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
OPENAI_API_KEY=
SERP_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
GOOGLE_REDIRECT_URI=urn:ietf:wg:oauth:2.0:oob
GOOGLE_CALENDAR_ID=primary
AGENT_NAME=Atlas
PORT=8000
OPENAI_MODEL=gpt-4.1-mini
OPENAI_CLASSIFIER_MODEL=gpt-4.1-nano
OPENAI_TIMEOUT_SECONDS=20
SERP_CACHE_TTL_SECONDS=900
PLAYWRIGHT_TIMEOUT_MS=15000
MAX_TOOL_RESULTS=5
FINAL_RESPONSE_MAX_TOKENS=220
CLASSIFIER_MAX_TOKENS=80
PLANNING_MAX_TOKENS=180
WHATSAPP_API_VERSION=v21.0
```

## WhatsApp Setup

1. Create a Meta developer app.
2. Enable WhatsApp Cloud API.
3. Copy the permanent access token into `WHATSAPP_ACCESS_TOKEN`.
4. Copy the webhook verify token into `WHATSAPP_VERIFY_TOKEN`.
5. Subscribe the webhook to WhatsApp message events.
6. Point the webhook URL to `https://<your-railway-domain>/webhook`.
7. Send messages starting with `@Atlas` or the configured `AGENT_NAME`.

## Railway Deployment

1. Create a new Railway project.
2. Deploy this folder as a Dockerfile service.
3. Add all environment variables.
4. Railway will set `PORT`.
5. After deploy, set the Meta webhook callback URL to `/webhook`.
6. Verify with `GET /healthz`.

## Google OAuth Setup

1. Create a Google Cloud project.
2. Enable the Google Calendar API.
3. Create OAuth client credentials.
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
5. Generate a refresh token with calendar event scope.
6. Set `GOOGLE_REFRESH_TOKEN`.
7. Optionally set `GOOGLE_CALENDAR_ID`.

## Change Agent Name

Set `AGENT_NAME`. Example: `AGENT_NAME=Chief`.

Invocation becomes `@Chief <request>`.

## Test

Local run:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Webhook verify example:

```bash
curl "http://127.0.0.1:8000/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=123"
```

Sample webhook payload:

```bash
curl -X POST http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "metadata": {"phone_number_id": "123"},
          "messages": [{
            "from": "15551234567",
            "type": "text",
            "text": {"body": "@Atlas research top executive assistants for travel planning"}
          }]
        }
      }]
    }]
  }'
```

## Cost Optimization

- Stateless request handling.
- No database or persistent memory.
- Compact classifier prompt.
- One final formatting call per request when possible.
- Calendar actions skip extra post-tool LLM work.
- No embeddings.
- No background jobs.
- SerpAPI responses cached in-process.
- Playwright only used for explicit availability checks.
- Tool payloads are compact and capped.
