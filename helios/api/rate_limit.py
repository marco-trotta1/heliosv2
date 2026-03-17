from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitPolicy:
    window_seconds: int
    max_requests: int


class InMemoryRateLimiter:
    """Prototype-safe rate limiter to slow obvious abuse on public demos."""

    def __init__(self, policy: RateLimitPolicy) -> None:
        self.policy = policy
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.policy.window_seconds
        with self._lock:
            entries = self._hits[key]
            while entries and entries[0] < cutoff:
                entries.popleft()
            if len(entries) >= self.policy.max_requests:
                return False
            entries.append(now)
            return True


def enforce_rate_limit(request: Request) -> None:
    limiter: InMemoryRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return

    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    if limiter.allow(key):
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests. Slow down and try again in a minute.",
    )
