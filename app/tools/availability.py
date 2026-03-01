from __future__ import annotations

from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.config import settings


class AvailabilityTool:
    async def run(self, url: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "url": url,
            "available": False,
            "title": "",
            "status": "unknown",
        }
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.playwright_timeout_ms,
                )
                result["title"] = await page.title()
                result["available"] = response is not None and response.status < 400
                result["status"] = (
                    f"http_{response.status}" if response is not None else "no_response"
                )
                await browser.close()
        except PlaywrightTimeoutError:
            result["status"] = "timeout"
        except Exception:
            result["status"] = "error"
        return result

