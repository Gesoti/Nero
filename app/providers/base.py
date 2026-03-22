"""
DataProvider protocol, shared domain dataclasses, and BaseProvider.

All country-specific providers must implement the DataProvider protocol.
Dataclasses are shared across all providers — they represent the normalised
domain model that the rest of the app (db.py, sync.py, routes) consumes.

BaseProvider supplies default implementations for close(), fetch_monthly_inflows(),
fetch_events(), and fetch_timeseries() so providers only override what they need.
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


# ── Shared base class ────────────────────────────────────────────────────────

class BaseProvider:
    """Concrete base with default implementations for common no-op methods.

    Subclasses must still implement fetch_dams(), fetch_percentages(), and
    fetch_date_statistics().  Override fetch_timeseries(), fetch_monthly_inflows(),
    or fetch_events() only when the upstream source provides that data.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        return []

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(self, date_from: date, date_until: date) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ── Shared zero-fill utilities ────────────────────────────────────────────────

def zero_fill_snapshot(
    dams: list[DamInfo], total_capacity_mcm: float, target_date: date
) -> PercentageSnapshot:
    """Return an all-zeros snapshot — used when upstream is unreachable or not yet parsed."""
    return PercentageSnapshot(
        date=target_date,
        dam_percentages=[
            DamPercentage(dam_name_en=d.name_en, percentage=0.0) for d in dams
        ],
        total_percentage=0.0,
        total_capacity_mcm=total_capacity_mcm,
    )


def zero_fill_date_statistics(
    dams: list[DamInfo], target_date: date
) -> DateStatistics:
    """Return zero-fill date statistics — used when upstream is unreachable."""
    return DateStatistics(
        date=target_date,
        dam_statistics=[
            DamStatistic(dam_name_en=d.name_en, storage_mcm=0.0, inflow_mcm=0.0)
            for d in dams
        ],
    )
