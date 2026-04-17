from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Final

from fastapi import HTTPException, Request, status


RATE_LIMIT_DETAIL: Final = "Too many requests. Slow down and try again in a minute."


@dataclass(frozen=True)
class RateLimitPolicy:
    window_seconds: int
    max_requests: int


class InMemoryRateLimiter:
    """Lightweight process-local guardrail for demo deployments."""

    def __init__(self, policy: RateLimitPolicy) -> None:
        self.policy = policy
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _evict_expired(self, entries: deque[float], cutoff: float) -> None:
        while entries and entries[0] < cutoff:
            entries.popleft()

    def allow(self, key: str) -> bool:
        current_time = time.monotonic()
        with self._lock:
            entries = self._hits[key]
            self._evict_expired(entries, current_time - self.policy.window_seconds)
            if len(entries) >= self.policy.max_requests:
                return False
            entries.append(current_time)
            return True


def _rate_limit_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{request.method}:{client_host}:{request.url.path}"


def enforce_rate_limit(request: Request) -> None:
    limiter: InMemoryRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return

    if limiter.allow(_rate_limit_key(request)):
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=RATE_LIMIT_DETAIL,
    )
