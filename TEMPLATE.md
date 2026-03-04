# Railway Template Notes

1. Keep the repository root deployment-ready.
2. Keep `Dockerfile` at the repo root.
3. Keep `railway.json` at the repo root.
4. Mark the repo as a Railway template from the Railway dashboard.
5. Add template metadata in Railway:
   - Name: Atlas Assistant
   - Description: WhatsApp-based executive assistant with full and execute modes
6. Document required variables in the Railway template UI:

```text
OPENAI_API_KEY
SERP_API_KEY
WHATSAPP_VERIFY_TOKEN
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_BASE_URL
PORT
```

7. Recommend attaching a persistent volume mounted at `/data` for Google OAuth token persistence.

