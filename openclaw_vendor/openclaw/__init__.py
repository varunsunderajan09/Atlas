from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Union


ToolHandler = Union[Callable[..., Any], Callable[..., Awaitable[Any]]]


@dataclass
class Tool:
    name: str
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def clear(self) -> None:
        self._tools.clear()


class Orchestrator:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def prepare(self, query: str, intent: dict[str, Any]) -> dict[str, Any]:
        return {"query": query, "intent": intent, "tools": list(self.registry._tools)}

    async def run(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        tool = self.registry.get(tool_name)
        if tool is None:
            raise KeyError(f"Tool not registered: {tool_name}")
        result = tool.handler(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result
