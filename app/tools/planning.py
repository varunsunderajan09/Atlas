from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


class PlanningTool:
    async def run(self, request_text: str, research_results: list[dict[str, Any]]) -> dict[str, Any]:
        if not settings.openai_api_key:
            return {"days": []}

        prompt = {
            "request": request_text,
            "candidates": research_results[:5],
        }
        payload = {
            "model": settings.openai_small_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Create a concise itinerary JSON. "
                        'Return {"days":[{"label":"","items":["",""]}]}. '
                        "Use at most 3 days and at most 3 items per day."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
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
        return json.loads(data["choices"][0]["message"]["content"])

