from __future__ import annotations

from typing import Any

import httpx

from app.cache import TTLCache
from app.config import settings


class ResearchTool:
    def __init__(self, cache: TTLCache) -> None:
        self.cache = cache

    async def run(self, query: str) -> dict[str, Any]:
        normalized_query = " ".join(query.split()).strip().lower()
        cached = self.cache.get(normalized_query)
        if cached is not None:
            return {"query": query, "cached": True, "results": cached}

        if not settings.serp_api_key:
            return {"query": query, "cached": False, "results": []}

        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.serp_api_key,
            "num": settings.max_tool_results,
        }

        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            payload = response.json()

        results = []
        for item in payload.get("organic_results", [])[: settings.max_tool_results]:
            results.append(
                {
                    "name": item.get("title", ""),
                    "rating": "",
                    "summary": item.get("snippet", ""),
                    "url": item.get("link", ""),
                }
            )

        self.cache.set(normalized_query, results)
        return {"query": query, "cached": False, "results": results}

