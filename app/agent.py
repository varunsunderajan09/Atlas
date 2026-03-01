from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from openclaw import Orchestrator, Tool, ToolRegistry

from app.cache import TTLCache
from app.config import settings
from app.tools.availability import AvailabilityTool
from app.tools.booking_links import BookingLinkTool
from app.tools.calendar_tool import GoogleCalendarTool
from app.tools.planning import PlanningTool
from app.tools.research import ResearchTool


class AtlasAgent:
    def __init__(self) -> None:
        self.research_tool = ResearchTool(
            TTLCache(ttl_seconds=settings.serp_cache_ttl_seconds)
        )
        self.planning_tool = PlanningTool()
        self.availability_tool = AvailabilityTool()
        self.booking_link_tool = BookingLinkTool()
        self.calendar_tool = GoogleCalendarTool()
        self.openclaw_adapter = OpenClawAdapter()

    async def handle(self, cleaned_text: str) -> str:
        intent = await self._classify(cleaned_text)
        return await self.openclaw_adapter.execute(cleaned_text, intent, self)

    async def _classify(self, cleaned_text: str) -> dict[str, Any]:
        fallback = self._heuristic_classify(cleaned_text)
        if not settings.openai_api_key:
            return fallback

        system_prompt = (
            "Classify the user request for a tool-using executive assistant. "
            "Return JSON only with keys: "
            "intent, needs_research, needs_plan, needs_availability, needs_booking_link, "
            "needs_calendar, target_url, booking_query, calendar_request. "
            "Use booleans where possible. "
            "Intent must be one of: research, planning, comparison, availability, booking, calendar, general. "
            "Do not include extra keys."
        )

        payload = {
            "model": settings.openai_classifier_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": cleaned_text},
            ],
            "temperature": 0,
            "max_tokens": settings.classifier_max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:
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
                parsed = json.loads(content)
                return {**fallback, **parsed}
        except Exception:
            return fallback
        return fallback

    def _heuristic_classify(self, cleaned_text: str) -> dict[str, Any]:
        lower = cleaned_text.lower()
        url_match = re.search(r"https?://\S+", cleaned_text)
        needs_calendar = any(
            phrase in lower
            for phrase in ("add to calendar", "put on my calendar", "schedule")
        )
        needs_availability = "availability" in lower or "available" in lower
        needs_booking_link = "booking link" in lower or "book" in lower
        needs_plan = any(term in lower for term in ("plan", "itinerary", "roadmap"))
        needs_research = any(
            term in lower for term in ("research", "find", "compare", "best", "vendor")
        )
        intent = "general"
        if needs_calendar:
            intent = "calendar"
        elif needs_availability:
            intent = "availability"
        elif needs_booking_link:
            intent = "booking"
        elif "compare" in lower or "vendor" in lower:
            intent = "comparison"
        elif needs_plan:
            intent = "planning"
        elif needs_research:
            intent = "research"

        return {
            "intent": intent,
            "needs_research": needs_research,
            "needs_plan": needs_plan,
            "needs_availability": needs_availability,
            "needs_booking_link": needs_booking_link,
            "needs_calendar": needs_calendar,
            "target_url": url_match.group(0) if url_match else "",
            "booking_query": cleaned_text,
            "calendar_request": self._extract_calendar_request(cleaned_text),
        }

    def _extract_calendar_request(self, cleaned_text: str) -> dict[str, Any]:
        start = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        return {
            "title": cleaned_text[:80],
            "description": cleaned_text,
            "start": start.isoformat(),
            "end": (start + timedelta(hours=1)).isoformat(),
            "location": "",
        }

    async def run_tools(self, cleaned_text: str, intent: dict[str, Any]) -> dict[str, Any]:
        tool_output: dict[str, Any] = {"intent": intent.get("intent", "general")}

        if intent.get("needs_calendar"):
            tool_output["calendar"] = self.calendar_tool.run(intent.get("calendar_request") or {})
            return tool_output

        if intent.get("needs_research") or intent.get("intent") in {"research", "comparison"}:
            tool_output["research"] = await self.research_tool.run(cleaned_text)

        if intent.get("needs_plan") or intent.get("intent") == "planning":
            tool_output["plan"] = await self.planning_tool.run(cleaned_text)

        if intent.get("needs_availability") and intent.get("target_url"):
            tool_output["availability"] = await self.availability_tool.run(intent["target_url"])

        if intent.get("needs_booking_link") or intent.get("intent") == "booking":
            tool_output["booking_links"] = self.booking_link_tool.run(
                intent.get("booking_query") or cleaned_text
            )

        return tool_output

    async def finalize(self, cleaned_text: str, tool_output: dict[str, Any]) -> str:
        if "calendar" in tool_output:
            event = tool_output["calendar"]
            return f"Scheduled: {event['title']}\nStart: {event['start']}\nLink: {event['link']}"

        if not settings.openai_api_key:
            return self._format_without_llm(tool_output)

        system_prompt = (
            "You are Atlas, a concise executive assistant. "
            "Use the supplied tool output only. "
            "Return a short, structured plaintext answer. "
            "No emojis. No filler. Prefer bullets only if needed."
        )
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"request": cleaned_text, "tool_output": tool_output},
                        ensure_ascii=True,
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": settings.final_response_max_tokens,
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
        return data["choices"][0]["message"]["content"].strip()

    def _format_without_llm(self, tool_output: dict[str, Any]) -> str:
        if tool_output.get("plan", {}).get("plan"):
            lines = []
            for index, item in enumerate(tool_output["plan"]["plan"], start=1):
                lines.append(f"{index}. {item.get('step', '')} [{item.get('timing', '')}]")
            return "\n".join(lines) or "No plan available."
        if tool_output.get("research", {}).get("results"):
            lines = []
            for item in tool_output["research"]["results"][:3]:
                lines.append(f"- {item['name']}: {item['url']}")
            return "\n".join(lines)
        if tool_output.get("availability"):
            item = tool_output["availability"]
            return f"{item['url']} {item['status']}"
        if tool_output.get("booking_links", {}).get("links"):
            return "\n".join(
                f"{item['label']}: {item['url']}"
                for item in tool_output["booking_links"]["links"]
            )
        return "No action taken."


class OpenClawAdapter:
    def __init__(self) -> None:
        self.registry = ToolRegistry()
        self.orchestrator = Orchestrator(self.registry)

    async def execute(
        self,
        cleaned_text: str,
        intent: dict[str, Any],
        agent: AtlasAgent,
    ) -> str:
        self.registry.clear()
        self.registry.register(Tool(name="research", handler=agent.research_tool.run))
        self.registry.register(Tool(name="planning", handler=agent.planning_tool.run))
        self.registry.register(Tool(name="availability", handler=agent.availability_tool.run))
        self.registry.register(
            Tool(name="booking_links", handler=agent.booking_link_tool.run)
        )
        self.registry.register(Tool(name="calendar", handler=agent.calendar_tool.run))
        await self.orchestrator.prepare(cleaned_text, intent)
        tool_output = await agent.run_tools(cleaned_text, intent)
        return await agent.finalize(cleaned_text, tool_output)
