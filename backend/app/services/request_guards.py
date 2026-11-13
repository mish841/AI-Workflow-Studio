"""Low-complexity request guards for paid model calls and abuse.

These do not replace authentication. The API is intended for local or
private use. Do not expose it to the public internet with a live API key.
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Deque

from fastapi import HTTPException

_TRUE = {"1", "true", "yes", "on"}


def paid_openai_enabled() -> bool:
    return os.getenv("PAID_OPENAI_ENABLED", "true").lower() in _TRUE


def require_paid_openai() -> None:
    if not paid_openai_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Paid language-model calls are disabled on this server. "
                "This prototype is meant to run locally, not as a public API."
            ),
        )


class SlidingWindowLimiter:
    """In-process limiter. Not a substitute for a reverse proxy."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: Deque[float] = deque()
        self._lock = threading.Lock()

    def check(self) -> None:
        now = time.monotonic()
        with self._lock:
            cutoff = now - self.window_seconds
            while self._hits and self._hits[0] < cutoff:
                self._hits.popleft()
            if len(self._hits) >= self.max_calls:
                raise HTTPException(
                    status_code=429,
                    detail="Too many assessment requests. Wait a few minutes and try again.",
                )
            self._hits.append(now)


# A full 18-requirement evaluation is expensive. Keep the local demo usable
# while blocking accidental loops.
evaluation_limiter = SlidingWindowLimiter(max_calls=4, window_seconds=15 * 60)
workflow_run_limiter = SlidingWindowLimiter(max_calls=8, window_seconds=15 * 60)
retrieval_limiter = SlidingWindowLimiter(max_calls=30, window_seconds=60)
