"""
Poland data provider — MVP stub.

Upstream source:
  IMGW daily PDF bulletin — Codzienny Biuletyn Hydrologiczny.
  URL: https://res2.imgw.pl/products/hydro/monitor-lite-products/BIULETYN_CODZIENNY.pdf
  Format: PDF (overwritten daily). Contains fill levels for ~19 major reservoirs.
  Parsing: requires pdfplumber (deferred to future sprint).

This stub downloads the IMGW PDF to verify network connectivity and logs its
file size. All fill percentages default to 0.0 until PDF parsing is implemented.
The scheduler retries at the next sync interval, so 0.0 is safe and expected.
"""
from __future__ import annotations

import logging
from datetime import date

import httpx

from app.providers.base import (
    BaseProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    zero_fill_date_statistics,
    zero_fill_snapshot,
)

logger = logging.getLogger(__name__)

# ── Hardcoded reservoir metadata ──────────────────────────────────────────────
# Top 15 Polish reservoirs by capacity (MCM = hm³).
# name_en: ASCII form used in URLs and DB keys.
# name_el: Polish display name (diacritic-safe for display; name_en is ASCII only).
# Coordinates are approximate dam centre points (WGS84).

_POLAND_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Solina", name_el="Solina",
        capacity_mcm=472.0, capacity_m3=int(472.0 * 1_000_000),
        lat=49.38, lng=22.45,
        height=82, year_built=1968,
        river_name_el="San", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Wloclawek", name_el="Włocławek",
        capacity_mcm=453.6, capacity_m3=int(453.6 * 1_000_000),
        lat=52.62, lng=19.40,
        height=14, year_built=1970,
        river_name_el="Wisła", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Czorsztyn", name_el="Czorsztyn",
        capacity_mcm=238.6, capacity_m3=int(238.6 * 1_000_000),
        lat=49.44, lng=20.32,
        height=56, year_built=1997,
        river_name_el="Dunajec", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Jeziorsko", name_el="Jeziorsko",
        capacity_mcm=193.1, capacity_m3=int(193.1 * 1_000_000),
        lat=51.74, lng=18.63,
        height=14, year_built=1986,
        river_name_el="Warta", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Goczalkowice", name_el="Goczałkowice",
        capacity_mcm=161.3, capacity_m3=int(161.3 * 1_000_000),
        lat=49.93, lng=18.97,
        height=15, year_built=1956,
        river_name_el="Wisła", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Swinna-Poreba", name_el="Świnna Poręba",
        capacity_mcm=160.8, capacity_m3=int(160.8 * 1_000_000),
        lat=49.72, lng=19.83,
        height=55, year_built=2011,
        river_name_el="Skawa", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Roznow", name_el="Rożnów",
        capacity_mcm=155.8, capacity_m3=int(155.8 * 1_000_000),
        lat=49.76, lng=20.68,
        height=40, year_built=1941,
        river_name_el="Dunajec", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Dobczyce", name_el="Dobczyce",
        capacity_mcm=137.7, capacity_m3=int(137.7 * 1_000_000),
        lat=49.87, lng=20.08,
        height=42, year_built=1986,
        river_name_el="Raba", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Otmuchow", name_el="Otmuchów",
        capacity_mcm=129.2, capacity_m3=int(129.2 * 1_000_000),
        lat=50.47, lng=17.18,
        height=25, year_built=1933,
        river_name_el="Nysa Kłodzka", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nysa", name_el="Nysa",
        capacity_mcm=121.7, capacity_m3=int(121.7 * 1_000_000),
        lat=50.43, lng=17.25,
        height=36, year_built=1971,
        river_name_el="Nysa Kłodzka", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Debe", name_el="Dębe",
        capacity_mcm=96.0, capacity_m3=int(96.0 * 1_000_000),
        lat=52.47, lng=20.88,
        height=17, year_built=1963,
        river_name_el="Bug", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Tresna", name_el="Tresna",
        capacity_mcm=92.7, capacity_m3=int(92.7 * 1_000_000),
        lat=49.68, lng=19.18,
        height=46, year_built=1966,
        river_name_el="Soła", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Turawa", name_el="Turawa",
        capacity_mcm=92.6, capacity_m3=int(92.6 * 1_000_000),
        lat=50.72, lng=18.10,
        height=23, year_built=1938,
        river_name_el="Mała Panew", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Sulejow", name_el="Sulejów",
        capacity_mcm=84.3, capacity_m3=int(84.3 * 1_000_000),
        lat=51.37, lng=19.87,
        height=17, year_built=1973,
        river_name_el="Pilica", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Dzierzno-Duze", name_el="Dzierżno Duże",
        capacity_mcm=84.3, capacity_m3=int(84.3 * 1_000_000),
        lat=50.37, lng=18.57,
        height=16, year_built=1963,
        river_name_el="Kłodnica", type_el="Zapora",
        image_url="", wikipedia_url="",
    ),
]

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _POLAND_DAMS)

# IMGW PDF bulletin path — fetched to verify connectivity.
# The PDF is overwritten daily at the same URL, so HEAD or GET retrieves the latest.
_IMGW_PDF_PATH = "/products/hydro/monitor-lite-products/BIULETYN_CODZIENNY.pdf"


class PolandProvider(BaseProvider):
    """DataProvider stub for Polish reservoir data (IMGW PDF bulletin).

    Probes the IMGW PDF endpoint to verify upstream connectivity and logs the
    response size. All fill percentages are returned as 0.0 until pdfplumber
    parsing is implemented in a future sprint. On any connectivity error the
    stub returns zero-fill defaults without raising — the scheduler retries
    at the next sync interval.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client)

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_POLAND_DAMS)

    async def _probe_upstream(self) -> None:
        """Fetch IMGW PDF and log its size for monitoring."""
        try:
            response = await self._client.get(_IMGW_PDF_PATH)
            logger.info(
                "IMGW PDF probe: HTTP %d, %d bytes",
                response.status_code,
                len(response.content),
            )
        except httpx.RequestError as exc:
            logger.warning("IMGW PDF probe failed: %s", exc)

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Probe upstream to log connectivity; actual PDF parsing deferred to future sprint.
        await self._probe_upstream()
        return zero_fill_snapshot(_POLAND_DAMS, _TOTAL_CAPACITY_MCM, target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        return zero_fill_date_statistics(_POLAND_DAMS, target_date)
