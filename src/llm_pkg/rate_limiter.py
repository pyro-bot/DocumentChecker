import asyncio
import logging
import os
import threading
import time
from typing import Optional


logger = logging.getLogger(__name__)


def _get_default_requests_per_minute() -> float:
    raw_value = os.getenv("LLM_REQUESTS_PER_MINUTE", "0").strip()
    try:
        return float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid LLM_REQUESTS_PER_MINUTE=%r; falling back to disabled rate limit",
            raw_value,
        )
        return 0.0


def _resolve_requests_per_minute(requests_per_minute: Optional[float]) -> float:
    if requests_per_minute is None:
        return _get_default_requests_per_minute()
    return float(requests_per_minute)


class LLMRequestQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_available_at_by_model: dict[str, float] = {}

    def _reserve_turn(self, model: str, requests_per_minute: float) -> float:
        if requests_per_minute <= 0:
            return 0.0

        interval_seconds = 60.0 / requests_per_minute
        now = time.monotonic()

        with self._lock:
            next_available_at = self._next_available_at_by_model.get(model, 0.0)
            scheduled_at = max(now, next_available_at)
            self._next_available_at_by_model[model] = scheduled_at + interval_seconds

        return scheduled_at - now

    def wait_for_turn(self, model: str, requests_per_minute: Optional[float] = None) -> float:
        resolved_requests_per_minute = _resolve_requests_per_minute(requests_per_minute)
        wait_seconds = self._reserve_turn(model, resolved_requests_per_minute)
        if wait_seconds > 0:
            logger.info(
                "User LLM request queued for %.1f seconds: model=%s rpm=%.2f",
                wait_seconds,
                model,
                resolved_requests_per_minute,
            )
            time.sleep(wait_seconds)

        return wait_seconds

    async def wait_for_turn_async(self, model: str, requests_per_minute: Optional[float] = None) -> float:
        resolved_requests_per_minute = _resolve_requests_per_minute(requests_per_minute)
        wait_seconds = self._reserve_turn(model, resolved_requests_per_minute)
        if wait_seconds > 0:
            logger.info(
                "User LLM request queued for %.1f seconds: model=%s rpm=%.2f",
                wait_seconds,
                model,
                resolved_requests_per_minute,
            )
            await asyncio.sleep(wait_seconds)

        return wait_seconds


llm_request_queue = LLMRequestQueue()
