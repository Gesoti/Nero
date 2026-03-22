"""
DataProvider protocol, shared domain dataclasses, BaseProvider mixin, and
shared zero-fill utilities.

All country-specific providers must implement the DataProvider protocol.
Dataclasses are shared across all providers — they represent the normalised
domain model that the rest of the app (db.py, sync.py, routes) consumes.

BaseProvider provides default no-op implementations for the methods that stub
providers (Austria, Bulgaria, Poland, Germany) don't need to override, so
those classes only implement what they actually do differently.

zero_fill_snapshot / zero_fill_date_statistics are shared helpers for
providers that cannot yet parse their upstream source and return 0.0 for all
dams. Centralising them eliminates copy-paste across stub providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

import httpx


# ── Domain dataclasses ────────────────────────────────────────────────────────

@dataclass
class DamInfo:
    name_en: str
    name_el: str
    capacity_m3: int
    capacity_mcm: float
    lat: float
    lng: float
    height: int
    year_built: int
    river_name_el: str
    type_el: str
    image_url: str
    wikipedia_url: str


@dataclass
class DamPercentage:
    dam_name_en: str
    percentage: float  # 0-1


@dataclass
class PercentageSnapshot:
    date: date
    dam_percentages: list[DamPercentage]
    total_percentage: float
    total_capacity_mcm: float


@dataclass
class DamStatistic:
    dam_name_en: str
    storage_mcm: float
    inflow_mcm: float


@dataclass
class DateStatistics:
    date: date
    dam_statistics: list[DamStatistic]


@dataclass
class MonthlyInflow:
    year: int
    period: str
    period_order: int
    inflow_mcm: float


@dataclass
class WaterEvent:
    name_en: str
    name_el: str
    event_type: str
    description: str
    date_from: date
    date_until: date


class UpstreamAPIError(Exception):
    """Raised when the upstream API is unreachable or returns an error."""
    pass


# ── DataProvider protocol ─────────────────────────────────────────────────────

@runtime_checkable
class DataProvider(Protocol):
    """Interface that every country data source must implement."""

    async def fetch_dams(self) -> list[DamInfo]: ...

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot: ...

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics: ...

    async def fetch_timeseries(self) -> list[PercentageSnapshot]: ...

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]: ...

    async def fetch_events(self, date_from: date, date_until: date) -> list[WaterEvent]: ...

    async def close(self) -> None: ...


# ── Shared zero-fill utilities ────────────────────────────────────────────────
# Used by stub providers that cannot yet parse their upstream source.
# Centralising here avoids copy-paste across Austria, Bulgaria, Poland, Germany.

def zero_fill_snapshot(
    dams: list[DamInfo],
    total_capacity_mcm: float,
    target_date: date,
) -> PercentageSnapshot:
    """Return a PercentageSnapshot with 0.0 for every dam in *dams*.

    The total_capacity_mcm is passed explicitly so callers can pre-compute it
    once at module level rather than summing on every call.
    """
    return PercentageSnapshot(
        date=target_date,
        dam_percentages=[
            DamPercentage(dam_name_en=d.name_en, percentage=0.0) for d in dams
        ],
        total_percentage=0.0,
        total_capacity_mcm=total_capacity_mcm,
    )


def zero_fill_date_statistics(
    dams: list[DamInfo],
    target_date: date,
) -> DateStatistics:
    """Return a DateStatistics with 0.0 storage/inflow for every dam in *dams*."""
    return DateStatistics(
        date=target_date,
        dam_statistics=[
            DamStatistic(dam_name_en=d.name_en, storage_mcm=0.0, inflow_mcm=0.0)
            for d in dams
        ],
    )


# ── BaseProvider ──────────────────────────────────────────────────────────────
# Concrete base class with default implementations for the methods that stub
# providers all share: store client, close client, and return [] for timeseries,
# monthly inflows, and events.  Subclasses only override what differs.

class BaseProvider:
    """Default implementations shared by all DataProvider subclasses.

    Subclasses must implement fetch_dams(), fetch_percentages(), and
    fetch_date_statistics(). Everything else defaults to no-op / empty list.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        return []

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(
        self, date_from: date, date_until: date
    ) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
