from __future__ import annotations

from typing import Any

import httpx

from app.cache import TTLCache
from app.config import settings


class SerpSearchTool:
    def __init__(self) -> None:
        self.cache = TTLCache(
            ttl_seconds=settings.serp_cache_ttl_seconds,
            max_size=settings.serp_cache_max_size,
        )

    async def run(self, query: str, category: str = "general") -> dict[str, Any]:
        cache_key = f"{category}:{' '.join(query.lower().split())}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return {"query": query, "category": category, "results": cached, "cached": True}

        if not settings.serp_api_key:
            return {"query": query, "category": category, "results": [], "cached": False}

        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.serp_api_key,
            "num": 5,
        }
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            payload = response.json()

        results = []
        for item in payload.get("organic_results", [])[:5]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "summary": item.get("snippet", ""),
                    "rating": item.get("rating") or item.get("rich_snippet", {})
                    .get("top", {})
                    .get("detected_extensions", {})
                    .get("rating", ""),
                    "price": item.get("price", ""),
                    "url": item.get("link", ""),
                }
            )

        self.cache.set(cache_key, results)
        return {"query": query, "category": category, "results": results, "cached": False}

