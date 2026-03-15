"""
Germany data provider — MVP stub.

Upstream sources (parsing deferred to future sprint):
  - Talsperrenleitzentrale Ruhr: https://www.talsperrenleitzentrale-ruhr.de
    9 dams in the Ruhr catchment, published via HTML pages.
  - Sachsen LTV: https://www.ltv.sachsen.de
    48 dams in Saxony, published via HTML pages.
  - Others: Thuringia (TLUG), Harz (Harzwasserwerke), Wupperverband — deferred.

This stub loads the Talsperrenleitzentrale Ruhr landing page to verify network
connectivity and logs the response size. All fill percentages default to 0.0
until the HTML parser is implemented. The scheduler retries at the next sync
interval, so 0.0 is safe and expected here.
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
    WaterEvent,
)

logger = logging.getLogger(__name__)

# ── Hardcoded reservoir metadata ──────────────────────────────────────────────
# Top 15 German reservoirs by capacity (MCM = hm³).
# name_en: ASCII form used in URLs and DB keys.
# name_el: German display name (umlaut-safe).
# Coordinates are approximate dam centre points (WGS84).

_GERMANY_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Bleiloch", name_el="Bleilochtalsperre",
        capacity_mcm=215.0, capacity_m3=int(215.0 * 1_000_000),
        lat=50.60, lng=11.70,
        height=63, year_built=1936,
        river_name_el="Saale", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Edersee", name_el="Edertalsperre",
        capacity_mcm=199.3, capacity_m3=int(199.3 * 1_000_000),
        lat=51.18, lng=9.07,
        height=48, year_built=1914,
        river_name_el="Eder", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Hohenwarte", name_el="Hohenwarte-Talsperre",
        capacity_mcm=182.0, capacity_m3=int(182.0 * 1_000_000),
        lat=50.63, lng=11.52,
        height=75, year_built=1942,
        river_name_el="Saale", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Bigge", name_el="Biggetalsperre",
        capacity_mcm=171.7, capacity_m3=int(171.7 * 1_000_000),
        lat=51.10, lng=7.89,
        height=49, year_built=1965,
        river_name_el="Bigge", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Mohne", name_el="Möhnetalsperre",
        capacity_mcm=134.5, capacity_m3=int(134.5 * 1_000_000),
        lat=51.49, lng=8.06,
        height=40, year_built=1913,
        river_name_el="Möhne", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Rappbode", name_el="Rappbodetalsperre",
        capacity_mcm=113.0, capacity_m3=int(113.0 * 1_000_000),
        lat=51.73, lng=10.89,
        height=106, year_built=1959,
        river_name_el="Rappbode", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Grosse-Dhuenn", name_el="Große Dhünn-Talsperre",
        capacity_mcm=81.0, capacity_m3=int(81.0 * 1_000_000),
        lat=51.07, lng=7.17,
        height=52, year_built=1985,
        river_name_el="Große Dhünn", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Eibenstock", name_el="Talsperre Eibenstock",
        capacity_mcm=76.4, capacity_m3=int(76.4 * 1_000_000),
        lat=50.50, lng=12.57,
        height=63, year_built=1975,
        river_name_el="Zwickauer Mulde", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Sorpe", name_el="Sorpetalsperre",
        capacity_mcm=70.4, capacity_m3=int(70.4 * 1_000_000),
        lat=51.35, lng=7.96,
        height=69, year_built=1935,
        river_name_el="Sorpe", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Poehl", name_el="Talsperre Pöhl",
        capacity_mcm=64.6, capacity_m3=int(64.6 * 1_000_000),
        lat=50.57, lng=12.18,
        height=66, year_built=1964,
        river_name_el="Trieb", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kriebstein", name_el="Talsperre Kriebstein",
        capacity_mcm=33.6, capacity_m3=int(33.6 * 1_000_000),
        lat=51.05, lng=13.02,
        height=37, year_built=1930,
        river_name_el="Zwickauer Mulde", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Verse", name_el="Versetalsperre",
        capacity_mcm=32.8, capacity_m3=int(32.8 * 1_000_000),
        lat=51.17, lng=7.69,
        height=52, year_built=1952,
        river_name_el="Verse", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Leibis-Lichte", name_el="Leibis-Lichte-Talsperre",
        capacity_mcm=32.8, capacity_m3=int(32.8 * 1_000_000),
        lat=50.57, lng=11.05,
        height=102, year_built=2006,
        river_name_el="Lichte", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Agger", name_el="Aggertalsperre",
        capacity_mcm=20.1, capacity_m3=int(20.1 * 1_000_000),
        lat=51.07, lng=7.62,
        height=57, year_built=1927,
        river_name_el="Agger", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Oker", name_el="Okertalsperre",
        capacity_mcm=46.6, capacity_m3=int(46.6 * 1_000_000),
        lat=51.87, lng=10.49,
        height=63, year_built=1956,
        river_name_el="Oker", type_el="Stausee",
        image_url="", wikipedia_url="",
    ),
]

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _GERMANY_DAMS)

# Talsperrenleitzentrale Ruhr landing page path — fetched to verify connectivity.
# Full parsing of water level data is deferred to a future sprint.
_RUHR_PROBE_PATH = "/"


def _zero_fill_snapshot(target_date: date) -> PercentageSnapshot:
    """Return an all-zeros snapshot for all 15 dams. Used until parsing is implemented."""
    return PercentageSnapshot(
        date=target_date,
        dam_percentages=[
            DamPercentage(dam_name_en=d.name_en, percentage=0.0)
            for d in _GERMANY_DAMS
        ],
        total_percentage=0.0,
        total_capacity_mcm=_TOTAL_CAPACITY_MCM,
    )


def _zero_fill_date_statistics(target_date: date) -> DateStatistics:
    """Return zero-fill date statistics for all 15 dams."""
    return DateStatistics(
        date=target_date,
        dam_statistics=[
            DamStatistic(dam_name_en=d.name_en, storage_mcm=0.0, inflow_mcm=0.0)
            for d in _GERMANY_DAMS
        ],
    )


class GermanyProvider:
    """DataProvider stub for German reservoir data.

    Probes the Talsperrenleitzentrale Ruhr website to verify upstream
    connectivity and logs the response size. All fill percentages are returned
    as 0.0 until the HTML parser is implemented in a future sprint.
    On any connectivity error, the stub falls back to zero-fill defaults
    without raising — the scheduler retries at the next sync interval.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_GERMANY_DAMS)

    async def _probe_upstream(self) -> None:
        """Fetch the Ruhr dam index page and log its size for monitoring."""
        try:
            response = await self._client.get(_RUHR_PROBE_PATH)
            logger.info(
                "Talsperrenleitzentrale Ruhr probe: HTTP %d, %d bytes",
                response.status_code,
                len(response.content),
            )
        except httpx.RequestError as exc:
            logger.warning("Talsperrenleitzentrale Ruhr probe failed: %s", exc)

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Probe upstream to log connectivity; actual parsing deferred to future sprint.
        await self._probe_upstream()
        return _zero_fill_snapshot(target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        return _zero_fill_date_statistics(target_date)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        # Historical data not consumed in MVP stub.
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
