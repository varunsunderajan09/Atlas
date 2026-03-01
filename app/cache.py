from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 900, max_size: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._data) >= self.max_size:
            oldest_key = min(self._data, key=lambda current: self._data[current][0])
            self._data.pop(oldest_key, None)
        self._data[key] = (time.time() + self.ttl_seconds, value)

