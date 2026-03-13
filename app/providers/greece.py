"""
Greece data provider — fetches from the EYDAP OpenData API.

Upstream: opendata-api-eydap.growthfund.gr
Covers 4 reservoirs serving Attica (Athens metro area, ~3.7M people):
Mornos, Yliki, Evinos, Marathon.
"""
from __future__ import annotations

import logging
from datetime import date

import httpx

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

logger = logging.getLogger(__name__)

# Hardcoded dam metadata — EYDAP API has no /dams endpoint
_GREECE_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Mornos", name_el="Μόρνος",
        capacity_m3=780_000_000, capacity_mcm=780.0,
        lat=38.585, lng=22.005,
        height=126, year_built=1979,
        river_name_el="Μόρνος", type_el="Χωμάτινο",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Yliki", name_el="Υλίκη",
        capacity_m3=600_000_000, capacity_mcm=600.0,
        lat=38.397, lng=23.247,
        height=0, year_built=0,
        river_name_el="", type_el="Φυσική λίμνη",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Evinos", name_el="Εύηνος",
        capacity_m3=130_000_000, capacity_mcm=130.0,
        lat=38.617, lng=21.837,
        height=125, year_built=2001,
        river_name_el="Εύηνος", type_el="Τοξωτό",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Marathon", name_el="Μαραθώνας",
        capacity_m3=41_000_000, capacity_mcm=41.0,
        lat=38.167, lng=23.900,
        height=54, year_built=1929,
        river_name_el="Χάραδρος", type_el="Βαρυτικό",
        image_url="", wikipedia_url="",
    ),
]


class GreeceProvider:
    """DataProvider implementation for the EYDAP OpenData API (Athens water supply)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_GREECE_DAMS)

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Stub — will be implemented in G3
        raise NotImplementedError("G3 will implement this")

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        raise NotImplementedError("G3 will implement this")

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        raise NotImplementedError("G3 will implement this")

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(self, date_from: date, date_until: date) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
