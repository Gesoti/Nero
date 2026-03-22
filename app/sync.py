"""
Data synchronisation layer.
initial_seed() populates an empty database; incremental_sync() refreshes
today's data on a schedule. Each upstream fetch is wrapped in tenacity retries
to handle transient API failures without crashing the app.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Callable, Coroutine, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.providers.base import DataProvider, UpstreamAPIError
from app.db import (
    update_sync_log,
    upsert_date_statistics,
    upsert_dams,
    upsert_events,
    upsert_monthly_inflows,
    upsert_percentage_snapshot,
)

logger = logging.getLogger(__name__)

# Shared retry config: 3 attempts, exponential back-off 2s → 30s cap
_RETRY_KWARGS = {
    "retry": retry_if_exception_type((httpx.HTTPError, UpstreamAPIError)),
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=30),
    "reraise": True,
}

_T = TypeVar("_T")


def _retried(fn: Callable[..., Coroutine[Any, Any, _T]]) -> Callable[..., Coroutine[Any, Any, _T]]:
    """Wrap an async callable with the shared tenacity retry policy."""
    return retry(**_RETRY_KWARGS)(fn)  # type: ignore[return-value]


async def initial_seed(provider: DataProvider, db_path: str) -> None:
    """
    Populate the database from scratch on first startup.
    Steps are sequential: dams must exist before percentages/statistics reference them.
    """
    today = date.today()
    logger.info("Starting initial seed for %s", today)

    logger.info("Fetching dam metadata")
    dams = await _retried(provider.fetch_dams)()
    upsert_dams(dams, db_path=db_path)

    logger.info("Fetching historical timeseries")
    snapshots = await _retried(provider.fetch_timeseries)()
    for snap in snapshots:
        upsert_percentage_snapshot(snap, db_path=db_path)
    logger.info("Stored %d snapshots", len(snapshots))

    logger.info("Fetching monthly inflows")
    inflows = await _retried(provider.fetch_monthly_inflows)()
    upsert_monthly_inflows(inflows, db_path=db_path)

    logger.info("Fetching events since Oct 2009")
    events = await _retried(provider.fetch_events)(date(2009, 10, 1), today)
    upsert_events(events, db_path=db_path)

    logger.info("Fetching today's statistics (%s)", today)
    stats = await _retried(provider.fetch_date_statistics)(today)
    upsert_date_statistics(stats, db_path=db_path)

    logger.info("Fetching today's percentages (%s)", today)
    pcts = await _retried(provider.fetch_percentages)(today)
    upsert_percentage_snapshot(pcts, db_path=db_path)

    update_sync_log("seed", today, db_path=db_path)
    logger.info("Initial seed complete")


async def incremental_sync(provider: DataProvider, db_path: str) -> None:
    """
    Refresh today's data. Called every N hours by the APScheduler.
    Non-fatal: if this fails, stale cached data continues serving requests.
    """
    today = date.today()
    logger.info("Incremental sync: %s", today)

    pcts = await _retried(provider.fetch_percentages)(today)
    upsert_percentage_snapshot(pcts, db_path=db_path)

    stats = await _retried(provider.fetch_date_statistics)(today)
    upsert_date_statistics(stats, db_path=db_path)

    inflows = await _retried(provider.fetch_monthly_inflows)()
    upsert_monthly_inflows(inflows, db_path=db_path)

    events = await _retried(provider.fetch_events)(date(2009, 10, 1), today)
    upsert_events(events, db_path=db_path)

    update_sync_log("incremental", today, db_path=db_path)
    logger.info("Incremental sync complete")
