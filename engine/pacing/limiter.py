"""Concurrency shaper for inference calls (stdlib only, sync).

Shapes free-tier NIM latency + 40 RPM + retry storms: caps in-flight calls,
enforces a minimum interval between starts, and exposes capped exponential
backoff for 429/handoff failures.
"""
from __future__ import annotations

import threading
import time

from engine import config as cfg


class RateLimiter:
    def __init__(self, max_in_flight: int = 3, min_interval_seconds: float = 1.6,
                 backoff_base_seconds: float = 2.0, backoff_max_seconds: float = 60.0):
        self.max_in_flight = int(max_in_flight)
        self.min_interval_seconds = float(min_interval_seconds)
        self.backoff_base_seconds = float(backoff_base_seconds)
        self.backoff_max_seconds = float(backoff_max_seconds)
        self._sem = threading.Semaphore(self.max_in_flight)
        self._lock = threading.Lock()
        self._last = 0.0

    @classmethod
    def from_config(cls) -> "RateLimiter":
        c = cfg.load_engine_config()["pacing"]
        return cls(
            c["max_in_flight"], c["min_interval_seconds"],
            c["backoff_base_seconds"], c["backoff_max_seconds"],
        )

    def backoff_delay(self, attempt: int) -> float:
        """Exponential backoff: base * 2^attempt, capped at max."""
        return min(self.backoff_base_seconds * (2 ** attempt),
                   self.backoff_max_seconds)

    def acquire(self):
        self._sem.acquire()
        with self._lock:
            now = time.monotonic()
            wait = self._last + self.min_interval_seconds - now
            self._last = now + max(wait, 0.0)
        if wait > 0:
            time.sleep(wait)

    def release(self):
        self._sem.release()
