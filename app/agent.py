from __future__ import annotations

import json
from typing import Any

import httpx
from openclaw import Orchestrator, Tool, ToolRegistry

from app.config import settings
from app.tools.availability import AvailabilityTool
from app.tools.booking_links import BookingLinksTool
from app.tools.calendar_tool import CalendarTool
from app.tools.parsing import (
    infer_simple_execution,
    parse_execution_block,
    strip_prefix,
    wants_availability,
    wants_booking_links,
    wants_calendar,
    wants_itinerary,
)
from app.tools.planning import PlanningTool
from app.tools.serp_search import SerpSearchTool


class AtlasAgent:
    def __init__(self) -> None:
        self.search_tool = SerpSearchTool()
        self.planning_tool = PlanningTool()
        self.availability_tool = AvailabilityTool()
        self.booking_tool = BookingLinksTool()
        self.calendar_tool = CalendarTool()
        self.registry = ToolRegistry()
        self.orchestrator = Orchestrator(self.registry)
        self._register_tools()

    def parse_invocation(self, message: str) -> tuple[str | None, str | None]:
        return strip_prefix(message)

    async def handle(self, mode: str, request_text: str) -> str:
        if mode == "execute":
            return await self._handle_execute(request_text)
        return await self._handle_full(request_text)

    def _register_tools(self) -> None:
        self.registry.register(Tool(name="serp_search", handler=self.search_tool.run))
        self.registry.register(Tool(name="planning", handler=self.planning_tool.run))
        self.registry.register(Tool(name="availability", handler=self.availability_tool.run))
        self.registry.register(Tool(name="booking_links", handler=self.booking_tool.run))
        self.registry.register(Tool(name="calendar", handler=self.calendar_tool.create_event))

    async def _handle_execute(self, request_text: str) -> str:
        plan = parse_execution_block(request_text)
        if plan is None:
            plan = infer_simple_execution(request_text)
            if not self._plan_is_structured_enough(plan, request_text) and settings.openai_api_key:
                plan = await self._llm_parse_execution(request_text)

        results: dict[str, Any] = {"mode": "execute"}
        query = plan.get("query") or request_text

        if plan.get("check_availability"):
            requested = plan.get("availability", {})
            results["availability"] = await self.orchestrator.run(
                "availability",
                requested.get("restaurant") or query,
                requested.get("date"),
                requested.get("time"),
                requested.get("party_size"),
            )

        if plan.get("create_booking_links"):
            booking = plan.get("booking", {})
            results["booking_links"] = await self.orchestrator.run(
                "booking_links",
                booking.get("query") or query,
                booking.get("date"),
                booking.get("time"),
                booking.get("party_size"),
            )

        if plan.get("create_calendar_event"):
            calendar = plan.get("calendar", {})
            results["calendar"] = await self.orchestrator.run(
                "calendar",
                calendar.get("summary") or query[:80],
                calendar.get("start_dt"),
                calendar.get("end_dt"),
                calendar.get("location"),
                calendar.get("description") or request_text,
            )

        return self._render_execute(results)

    async def _handle_full(self, request_text: str) -> str:
        intent = await self._classify_full_mode(request_text)
        search_results: list[dict[str, Any]] = []
        if intent["needs_research"]:
            category = intent.get("category", "general")
            search_payload = await self.orchestrator.run("serp_search", request_text, category)
            search_results = search_payload.get("results", [])

        results: dict[str, Any] = {
            "mode": "full",
            "request": request_text,
            "search_results": search_results,
        }

        if intent["needs_itinerary"] and search_results:
            results["itinerary"] = await self.orchestrator.run(
                "planning", request_text, search_results
            )

        if intent["needs_availability"]:
            results["availability"] = await self.orchestrator.run(
                "availability",
                intent.get("availability_target") or request_text,
                intent.get("date"),
                intent.get("time"),
                intent.get("party_size"),
            )

        if intent["needs_booking_links"]:
            results["booking_links"] = await self.orchestrator.run(
                "booking_links",
                intent.get("booking_query") or request_text,
                intent.get("date"),
                intent.get("time"),
                intent.get("party_size"),
            )

        if intent["needs_calendar"]:
            results["calendar"] = await self.orchestrator.run(
                "calendar",
                intent.get("calendar_summary") or request_text[:80],
                intent.get("calendar_start"),
                intent.get("calendar_end"),
                "",
                request_text,
            )

        return await self._render_full(request_text, results)

    def _plan_is_structured_enough(self, plan: dict[str, Any], request_text: str) -> bool:
        if plan.get("check_availability") or plan.get("create_calendar_event"):
            return True
        return bool(plan.get("query") or request_text.strip())

    async def _llm_parse_execution(self, request_text: str) -> dict[str, Any]:
        payload = {
            "model": settings.openai_small_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Convert the request into execution JSON only. "
                        'Return {"query":"","check_availability":false,"create_booking_links":false,'
                        '"create_calendar_event":false,"availability":{},"booking":{},'
                        '"calendar":{"summary":"","start_dt":"","end_dt":"","location":"","description":""}}.'
                    ),
                },
                {"role": "user", "content": request_text},
            ],
            "temperature": 0,
            "max_tokens": settings.execution_parse_max_tokens,
            "response_format": {"type": "json_object"},
        }
        data = await self._openai_chat(payload)
        return json.loads(data["choices"][0]["message"]["content"])

    async def _classify_full_mode(self, request_text: str) -> dict[str, Any]:
        fallback = {
            "needs_research": True,
            "needs_itinerary": wants_itinerary(request_text),
            "needs_availability": wants_availability(request_text),
            "needs_booking_links": wants_booking_links(request_text),
            "needs_calendar": wants_calendar(request_text),
            "category": self._infer_category(request_text),
            "availability_target": request_text,
            "booking_query": request_text,
            "calendar_summary": request_text[:80],
            "calendar_start": "",
            "calendar_end": "",
            "date": "",
            "time": "",
            "party_size": None,
        }
        if not settings.openai_api_key:
            return fallback

        payload = {
            "model": settings.openai_small_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify a full-mode travel and executive assistant request. "
                        "Return JSON only with keys: needs_research, needs_itinerary, "
                        "needs_availability, needs_booking_links, needs_calendar, category, "
                        "availability_target, booking_query, calendar_summary, calendar_start, "
                        "calendar_end, date, time, party_size. "
                        "category must be one of hotels, flights, restaurants, activities, general."
                    ),
                },
                {"role": "user", "content": request_text},
            ],
            "temperature": 0,
            "max_tokens": settings.classify_max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            data = await self._openai_chat(payload)
            return {**fallback, **json.loads(data["choices"][0]["message"]["content"])}
        except Exception:
            return fallback

    async def _render_full(self, request_text: str, results: dict[str, Any]) -> str:
        if not settings.openai_api_key:
            return self._render_full_fallback(results)

        payload = {
            "model": settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return concise WhatsApp-friendly plain text. "
                        "Use headings TOP OPTIONS, ITINERARY, AVAILABILITY, LINKS, CALENDAR when needed. "
                        "Keep it short. No HTML. No emojis. No filler."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"request": request_text, "results": results},
                        ensure_ascii=True,
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": settings.full_mode_max_tokens,
        }
        data = await self._openai_chat(payload)
        return data["choices"][0]["message"]["content"].strip()

    def _render_full_fallback(self, results: dict[str, Any]) -> str:
        lines = ["TOP OPTIONS"]
        for index, item in enumerate(results.get("search_results", [])[:5], start=1):
            lines.append(f"{index}. {item['title']}")
            if item.get("summary"):
                lines.append(item["summary"])
            if item.get("url"):
                lines.append(item["url"])
        itinerary = results.get("itinerary", {}).get("days", [])
        if itinerary:
            lines.append("")
            lines.append("ITINERARY")
            for day in itinerary:
                lines.append(day.get("label", "DAY"))
                for item in day.get("items", []):
                    lines.append(f"- {item}")
        if results.get("availability"):
            lines.append("")
            lines.append("AVAILABILITY")
            for slot in results["availability"].get("slots", []):
                lines.append(f"- {slot}")
        if results.get("booking_links"):
            lines.append("")
            lines.append("LINKS")
            for item in results["booking_links"]["links"]:
                lines.append(f"{item['label']}: {item['url']}")
        if results.get("calendar"):
            lines.append("")
            lines.append("CALENDAR")
            lines.append(f"Added: {results['calendar']['summary']}")
            lines.append(results["calendar"]["link"])
        return "\n".join(lines[:120])

    def _render_execute(self, results: dict[str, Any]) -> str:
        lines = ["DONE / RESULTS"]
        if results.get("availability"):
            lines.append("AVAILABILITY")
            availability = results["availability"]
            if availability.get("slots"):
                for slot in availability["slots"][:5]:
                    lines.append(f"- {slot}")
            else:
                lines.append(f"- Status: {availability.get('status', 'unknown')}")
            lines.append(availability.get("search_url", ""))
        if results.get("booking_links"):
            lines.append("LINKS")
            for item in results["booking_links"]["links"]:
                lines.append(f"{item['label']}: {item['url']}")
        if results.get("calendar"):
            lines.append("CALENDAR")
            lines.append(f"Added: {results['calendar']['summary']}")
            lines.append(f"Start: {results['calendar']['start']}")
            lines.append(results["calendar"]["link"])
        return "\n".join([line for line in lines if line][:120])

    def _infer_category(self, request_text: str) -> str:
        lower = request_text.lower()
        if "hotel" in lower:
            return "hotels"
        if "flight" in lower:
            return "flights"
        if "restaurant" in lower or "dinner" in lower:
            return "restaurants"
        if "activity" in lower or "things to do" in lower:
            return "activities"
        return "general"

    async def _openai_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
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
            return response.json()

