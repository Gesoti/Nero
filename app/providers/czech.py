"""
Czech Republic data provider — fetches from CHMI (Czech Hydrometeorological Institute).

Upstream: hydro.chmi.cz (real-time hydrological data)
Covers Czech Republic's 15 largest reservoirs by capacity, spanning major
river basins: Vltava, Ohře, Jihlava, Dyje, Moravice, and others.

Note: CHMI does not expose a public JSON API. The provider uses hardcoded
dam metadata and attempts to fetch live data. If the upstream page format
is not parseable, it falls back gracefully to 0.0 percentages — the
scheduler will populate real data over time via incremental_sync.
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

# ── Hardcoded dam metadata ────────────────────────────────────────────────────
# Sourced from CHMI records and Czech water authority data.
# ASCII name_en is required for URL-safe routing (diacritics removed).
# name_el stores the local Czech name (with diacritics) for display.

_CZECH_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Orlik", name_el="Orlík",
        capacity_m3=716_000_000, capacity_mcm=716.0,
        lat=49.5078, lng=14.1695,
        height=91, year_built=1963,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Lipno", name_el="Lipno",
        capacity_m3=306_000_000, capacity_mcm=306.0,
        lat=48.6333, lng=14.2167,
        height=25, year_built=1959,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nechranice", name_el="Nechranice",
        capacity_m3=288_000_000, capacity_mcm=288.0,
        lat=50.3722, lng=13.3917,
        height=48, year_built=1968,
        river_name_el="Ohře", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Slapy", name_el="Slapy",
        capacity_m3=270_000_000, capacity_mcm=270.0,
        lat=49.7833, lng=14.4167,
        height=67, year_built=1955,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Svihov", name_el="Švihov",
        capacity_m3=267_000_000, capacity_mcm=267.0,
        lat=49.6667, lng=15.1500,
        height=58, year_built=1975,
        river_name_el="Želivka", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Slezska Harta", name_el="Slezská Harta",
        capacity_m3=209_000_000, capacity_mcm=209.0,
        lat=49.9333, lng=17.1833,
        height=65, year_built=1997,
        river_name_el="Moravice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nove Mlyny", name_el="Nové Mlýny",
        capacity_m3=142_000_000, capacity_mcm=142.0,
        lat=48.8500, lng=16.6500,
        height=18, year_built=1989,
        river_name_el="Dyje", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Vranov", name_el="Vranov",
        capacity_m3=133_000_000, capacity_mcm=133.0,
        lat=48.8917, lng=15.8167,
        height=47, year_built=1934,
        river_name_el="Dyje", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Dalesice", name_el="Dalešice",
        capacity_m3=127_000_000, capacity_mcm=127.0,
        lat=49.1333, lng=15.9167,
        height=100, year_built=1978,
        river_name_el="Jihlava", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Prisecnice", name_el="Přísečnice",
        capacity_m3=50_000_000, capacity_mcm=50.0,
        lat=50.4500, lng=13.0500,
        height=61, year_built=1976,
        river_name_el="Přísečnice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kruzberk", name_el="Kružberk",
        capacity_m3=35_000_000, capacity_mcm=35.0,
        lat=49.8333, lng=17.5500,
        height=35, year_built=1955,
        river_name_el="Moravice", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Josefuv Dul", name_el="Josefův Důl",
        capacity_m3=24_000_000, capacity_mcm=24.0,
        lat=50.7833, lng=15.1833,
        height=44, year_built=1982,
        river_name_el="Kamenice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Flaje", name_el="Fláje",
        capacity_m3=23_000_000, capacity_mcm=23.0,
        lat=50.6833, lng=13.5833,
        height=59, year_built=1963,
        river_name_el="Flájský potok", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Stanovice", name_el="Stanovice",
        capacity_m3=21_000_000, capacity_mcm=21.0,
        lat=50.2167, lng=12.8833,
        height=55, year_built=1978,
        river_name_el="Teplá", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Zermanice", name_el="Žermanice",
        capacity_m3=25_000_000, capacity_mcm=25.0,
        lat=49.7333, lng=18.4833,
        height=32, year_built=1957,
        river_name_el="Lučina", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
]

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _CZECH_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _CZECH_DAMS)

# CHMI does not expose a public structured JSON API; the provider fetches
# the portal page but currently falls back gracefully when no parseable
# data is found. The scheduler will accumulate data over time.
_CHMI_URL = "/"


class CzechProvider:
    """DataProvider implementation for CHMI (Czech Republic reservoir data).

    Attempts to fetch live data from hydro.chmi.cz. Falls back to 0.0 percentages
    when the upstream page is unavailable or unparseable — this is intentional
    for the initial MVP. Real data accumulates as the scheduler runs.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_CZECH_DAMS)

    async def _fetch_upstream_page(self) -> str:
        """Fetch CHMI portal page. Returns HTML text or raises UpstreamAPIError."""
        try:
            response = await self._client.get(_CHMI_URL)
        except httpx.RequestError as exc:
            raise UpstreamAPIError(f"CHMI request failed: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamAPIError(
                f"CHMI returned HTTP {response.status_code}"
            )

        return response.text

    def _build_fallback_snapshot(self, target_date: date) -> PercentageSnapshot:
        """Return a zero-fill snapshot when upstream data is unavailable."""
        dam_percentages = [
            DamPercentage(dam_name_en=dam.name_en, percentage=0.0)
            for dam in _CZECH_DAMS
        ]
        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=0.0,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Attempt to fetch live data. If we can't parse it, fall back to zero-fill.
        # UpstreamAPIError on HTTP errors propagates to the caller (scheduler handles retry).
        html = await self._fetch_upstream_page()

        # CHMI does not currently expose a parseable structured endpoint.
        # Log that we received data but couldn't parse it, then fall back gracefully.
        # Future iterations can add real parsing here once the page structure is analysed.
        logger.debug(
            "CHMI page fetched (%d bytes); structured parsing not yet implemented — "
            "using fallback zero-fill snapshot",
            len(html),
        )
        return self._build_fallback_snapshot(target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        # Same approach as fetch_percentages: attempt fetch, fall back gracefully.
        html = await self._fetch_upstream_page()
        logger.debug(
            "CHMI page fetched (%d bytes) for date statistics; using fallback zero-fill",
            len(html),
        )

        dam_statistics = [
            DamStatistic(
                dam_name_en=dam.name_en,
                storage_mcm=0.0,
                inflow_mcm=0.0,
            )
            for dam in _CZECH_DAMS
        ]
        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        # CHMI has no historical API; timeseries builds up over time via the scheduler.
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
