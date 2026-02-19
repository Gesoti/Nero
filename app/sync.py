"""
Data synchronisation layer.
initial_seed() populates an empty database; incremental_sync() refreshes
today's data on a schedule. Each upstream fetch is wrapped in tenacity retries
to handle transient API failures without crashing the app.
"""
from __future__ import annotations

import logging
from datetime import date

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.api_client import (
    UpstreamAPIError,
    fetch_date_statistics,
    fetch_dams,
    fetch_events,
    fetch_monthly_inflows,
    fetch_percentages,
    fetch_timeseries,
)
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
_retry_kwargs = dict(
    retry=retry_if_exception_type((httpx.HTTPError, UpstreamAPIError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


async def initial_seed() -> None:
    """
    Populate the database from scratch on first startup.
    Steps are sequential: dams must exist before percentages/statistics reference them.
    """
    today = date.today()
    logger.info("Starting initial seed for %s", today)

    logger.info("  1/6 Fetching dam metadata")
    dams = await retry(**_retry_kwargs)(fetch_dams)()
    upsert_dams(dams)

    logger.info("  2/6 Fetching historical timeseries (~133 snapshots)")
    snapshots = await retry(**_retry_kwargs)(fetch_timeseries)()
    for snap in snapshots:
        upsert_percentage_snapshot(snap)
    logger.info("       Stored %d snapshots", len(snapshots))

    logger.info("  3/6 Fetching monthly inflows")
    inflows = await retry(**_retry_kwargs)(fetch_monthly_inflows)()
    upsert_monthly_inflows(inflows)

    logger.info("  4/6 Fetching events since Oct 2009")
    events = await retry(**_retry_kwargs)(fetch_events)(date(2009, 10, 1), today)
    upsert_events(events)

    logger.info("  5/6 Fetching today's statistics (%s)", today)
    stats = await retry(**_retry_kwargs)(fetch_date_statistics)(today)
    upsert_date_statistics(stats)

    logger.info("  6/6 Fetching today's percentages (%s)", today)
    pcts = await retry(**_retry_kwargs)(fetch_percentages)(today)
    upsert_percentage_snapshot(pcts)

    update_sync_log("seed", today)
    logger.info("Initial seed complete")


async def incremental_sync() -> None:
    """
    Refresh today's data. Called every N hours by the APScheduler.
    Non-fatal: if this fails, stale cached data continues serving requests.
    """
    today = date.today()
    logger.info("Incremental sync: %s", today)

    pcts = await retry(**_retry_kwargs)(fetch_percentages)(today)
    upsert_percentage_snapshot(pcts)

    stats = await retry(**_retry_kwargs)(fetch_date_statistics)(today)
    upsert_date_statistics(stats)

    inflows = await retry(**_retry_kwargs)(fetch_monthly_inflows)()
    upsert_monthly_inflows(inflows)

    events = await retry(**_retry_kwargs)(fetch_events)(date(2009, 10, 1), today)
    upsert_events(events)

    update_sync_log("incremental", today)
    logger.info("Incremental sync complete")
