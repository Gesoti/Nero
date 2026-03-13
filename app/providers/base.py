"""
DataProvider protocol and shared domain dataclasses.

All country-specific providers must implement the DataProvider protocol.
Dataclasses are shared across all providers — they represent the normalised
domain model that the rest of the app (db.py, sync.py, routes) consumes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


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
