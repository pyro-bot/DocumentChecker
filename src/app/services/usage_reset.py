import asyncio
import logging
import os
from typing import Optional

from ..database import ModelUsageRepository

logger = logging.getLogger(__name__)

USAGE_LIMIT_RESET_INTERVAL_ENV = "USAGE_LIMIT_RESET_INTERVAL_HOURS"


def usage_limit_reset_interval_hours() -> Optional[float]:
    raw_value = os.getenv(USAGE_LIMIT_RESET_INTERVAL_ENV, "").strip()
    if not raw_value:
        return None

    try:
        interval_hours = float(raw_value)
    except ValueError:
        logger.warning(
            "Ignoring invalid %s=%r: expected a positive number of hours",
            USAGE_LIMIT_RESET_INTERVAL_ENV,
            raw_value,
        )
        return None

    if interval_hours <= 0:
        return None

    return interval_hours


async def run_usage_limit_reset_loop() -> None:
    interval_hours = usage_limit_reset_interval_hours()
    if interval_hours is None:
        logger.info("Automatic usage limit reset is disabled")
        return

    interval_seconds = interval_hours * 60 * 60
    logger.info("Automatic usage limit reset enabled: every %s hour(s)", interval_hours)

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            reset_records = ModelUsageRepository().reset_usage()
            logger.info("Automatic usage limit reset completed: reset_records=%s", reset_records)
        except Exception:
            logger.exception("Automatic usage limit reset failed")
