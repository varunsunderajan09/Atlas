# Atlas Assistant

## One-click Deploy to Railway

1. Push this repo to GitHub.
2. In Railway, click `New Project`.
3. Choose `Deploy from GitHub repo` or deploy the repo as a Railway template.
4. Select this repository.
5. Railway will build from the included `Dockerfile`.
6. Add these environment variables before first production use:

```env
OPENAI_API_KEY=
SERP_API_KEY=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_BASE_URL=https://your-app.up.railway.app
PORT=8000
```

7. Redeploy after setting variables.
8. Open `https://your-app.up.railway.app/healthz`.

## Railway CLI Fallback

```bash
railway login
railway init
railway up
railway variables set OPENAI_API_KEY=...
railway variables set SERP_API_KEY=...
railway variables set WHATSAPP_VERIFY_TOKEN=...
railway variables set WHATSAPP_ACCESS_TOKEN=...
railway variables set WHATSAPP_PHONE_NUMBER_ID=...
railway variables set GOOGLE_CLIENT_ID=...
railway variables set GOOGLE_CLIENT_SECRET=...
railway variables set GOOGLE_REDIRECT_BASE_URL=https://your-app.up.railway.app
```

## WhatsApp Setup Checklist

1. Create a Meta app in Meta for Developers.
2. Add the WhatsApp product.
3. Copy the WhatsApp access token into `WHATSAPP_ACCESS_TOKEN`.
4. Copy the phone number ID into `WHATSAPP_PHONE_NUMBER_ID`.
5. Choose any random secret string and set it as `WHATSAPP_VERIFY_TOKEN`.
6. In Meta webhook settings, set:
   - Callback URL: `https://your-app.up.railway.app/webhook`
   - Verify Token: the exact same `WHATSAPP_VERIFY_TOKEN`
7. Subscribe the webhook to message events.
8. Send test messages:

```text
@atlas-full best hotels in soho for next week
@atlas-execute booking link for carbone tomorrow 8pm
```

Rules:
- Prefix matching is case-insensitive.
- Messages without `@atlas-full` or `@atlas-execute` are ignored.

## Google Calendar Setup Checklist

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable Google Calendar API.
4. Configure the OAuth consent screen.
5. Create OAuth credentials for `Web application`.
6. Add this redirect URI:

```text
https://your-app.up.railway.app/auth/google/callback
```

7. Set Railway variables:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_BASE_URL=https://your-app.up.railway.app`
8. Deploy or redeploy.
9. Visit:

```text
https://your-app.up.railway.app/auth/google/start
```

10. Complete Google sign-in and consent.
11. The app stores the encrypted token in `/data/google_token.enc` when a writable volume exists. If no volume exists, it stores the token in memory and logs a warning.

## Cost Controls

- `@atlas-execute` forbids SerpAPI.
- `@atlas-execute` uses pure parsing first and allows at most one LLM call only when parsing is not structured enough.
- `@atlas-execute` does not run planning and does not run multi-step loops.
- `@atlas-full` targets at most two LLM calls total: one classification call and one final rendering call.
- SerpAPI results are cached in memory with a 24-hour TTL.
- Playwright runs only when availability is explicitly requested.
- Calendar actions only run when explicitly requested.
- No database.
- No background processing.
- No payment execution.

## Local Run

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

