from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import settings


class AvailabilityTool:
    async def run(
        self,
        restaurant: str,
        date: str | None = None,
        time: str | None = None,
        party_size: int | None = None,
    ) -> dict[str, Any]:
        query = restaurant.strip()
        search_url = f"https://www.opentable.com/s?term={quote_plus(query)}"
        results: dict[str, Any] = {
            "restaurant": restaurant,
            "search_url": search_url,
            "slots": [],
            "status": "not_checked",
        }
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(search_url, timeout=settings.playwright_timeout_ms)
                buttons = await page.locator("a, button").all_inner_texts()
                slots = []
                for text in buttons:
                    text = " ".join(text.split())
                    if ":" not in text:
                        continue
                    if len(text) > 20:
                        continue
                    slots.append(text)
                    if len(slots) == 5:
                        break
                await browser.close()
                results["slots"] = slots
                results["status"] = "ok"
                results["requested"] = {
                    "date": date or "",
                    "time": time or "",
                    "party_size": party_size or "",
                }
        except PlaywrightTimeoutError:
            results["status"] = "timeout"
        except Exception:
            results["status"] = "error"
        return results

