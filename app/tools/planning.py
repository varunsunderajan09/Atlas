from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class PlanningTool:
    async def run(self, query: str) -> dict[str, Any]:
        if not settings.openai_api_key:
            return {"plan": []}

        system_prompt = (
            "Return a compact executive plan as JSON only. "
            'Schema: {"plan":[{"step":"", "owner":"", "timing":"", "notes":""}]}. '
            "Use at most 5 steps. Keep notes short."
        )

        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            "temperature": 0.2,
            "max_tokens": settings.planning_max_tokens,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str):
            import json

            return json.loads(content)
        return {"plan": []}

