"""
Backwards-compatibility shim — delegates to app.providers.cyprus.CyprusProvider.

All public names that existed before the refactoring are re-exported here so that
app/sync.py, app/db.py, app/main.py, and tests continue to work unchanged.
"""
from __future__ import annotations

from datetime import date

import httpx

from app.config import settings
from app.providers.base import (
    DamInfo,
    DamPercentage,
    DamStatistic,
    DateStatistics,
    MonthlyInflow,
    PercentageSnapshot,
    UpstreamAPIError,
    WaterEvent,
)
from app.providers.cyprus import CyprusProvider

# ── Re-exports for backwards compatibility ────────────────────────────────────
__all__ = [
    "DamInfo",
    "DamPercentage",
    "DamStatistic",
    "DateStatistics",
    "MonthlyInflow",
    "PercentageSnapshot",
    "UpstreamAPIError",
    "WaterEvent",
    "close_client",
    "fetch_dams",
    "fetch_percentages",
    "fetch_date_statistics",
    "fetch_timeseries",
    "fetch_monthly_inflows",
    "fetch_events",
]

# ── Shared provider instance (created lazily) ─────────────────────────────────
_provider: CyprusProvider | None = None


def _get_client() -> httpx.AsyncClient:
    """Get or create the shared httpx.AsyncClient (used by legacy patch targets in tests)."""
    return _get_provider()._client


def _get_provider() -> CyprusProvider:
    global _provider
    if _provider is None or _provider._client.is_closed:
        client = httpx.AsyncClient(
            base_url=settings.upstream_base_url,
            headers={"User-Agent": "CyprusWaterDashboard/1.0"},
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.upstream_timeout_seconds,
                write=5.0,
                pool=5.0,
            ),
        )
        _provider = CyprusProvider(client=client)
    return _provider


async def close_client() -> None:
    global _provider
    if _provider:
        await _provider.close()
        _provider = None


# ── Module-level functions that delegate to the provider ──────────────────────

async def fetch_dams() -> list[DamInfo]:
    return await _get_provider().fetch_dams()


async def fetch_percentages(target_date: date) -> PercentageSnapshot:
    return await _get_provider().fetch_percentages(target_date)


async def fetch_date_statistics(target_date: date) -> DateStatistics:
    return await _get_provider().fetch_date_statistics(target_date)


async def fetch_timeseries() -> list[PercentageSnapshot]:
    return await _get_provider().fetch_timeseries()


async def fetch_monthly_inflows() -> list[MonthlyInflow]:
    return await _get_provider().fetch_monthly_inflows()


async def fetch_events(date_from: date, date_until: date) -> list[WaterEvent]:
    return await _get_provider().fetch_events(date_from, date_until)
