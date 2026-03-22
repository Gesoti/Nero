"""
Austria data provider — Austrian Alpine hydroelectric reservoir levels.

Covers Austria's 15 largest reservoirs by capacity — primarily Alpine
hydroelectric storage dams in the states of Carinthia, Tyrol, and Vorarlberg.

Data source status (researched 2026-03-15):
- eHYD (ehyd.gv.at): River gauges, precipitation, groundwater only. NO reservoir fill data.
- VERBUND: Operates most dams but keeps fill data private (electricity trading).
- PegelAlarm: River water levels only, not reservoir storage.
- data.gv.at: Metadata only (locations, water rights), no fill levels.
- ENTSO-E: Electricity market data (MWh), not water — poor fit for a water dashboard.

No viable per-dam data source exists for Austria. Returns 0.0 for all dams.
Monitor data.gv.at for future Open Government Data releases.
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
    UpstreamAPIError,
    zero_fill_date_statistics,
    zero_fill_snapshot,
)

logger = logging.getLogger(__name__)

# ── Hardcoded dam metadata ────────────────────────────────────────────────────
# Austria's 15 largest reservoirs by capacity. All are Alpine hydroelectric
# storage dams. Coordinates verified against Google Maps and openstreetmap.org.
# ASCII name_en values (umlauts stripped) used as URL path identifiers.

_AUSTRIA_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Kolnbrein", name_el="Kölnbrein",
        capacity_m3=200_000_000, capacity_mcm=200.0,
        lat=47.0667, lng=13.3500,
        height=200, year_built=1978,
        river_name_el="Malta", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Gepatsch", name_el="Gepatsch",
        capacity_m3=139_000_000, capacity_mcm=139.0,
        lat=46.9167, lng=10.7000,
        height=153, year_built=1964,
        river_name_el="Fagge", type_el="Schüttdamm",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Schlegeis", name_el="Schlegeis",
        capacity_m3=126_000_000, capacity_mcm=126.0,
        lat=47.0333, lng=11.7167,
        height=131, year_built=1971,
        river_name_el="Zamser Bach", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Zillergrundl", name_el="Zillergründl",
        capacity_m3=90_000_000, capacity_mcm=90.0,
        lat=47.0333, lng=11.8833,
        height=186, year_built=1987,
        river_name_el="Ziller", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Zillergrund", name_el="Zillergrund",
        capacity_m3=85_000_000, capacity_mcm=85.0,
        lat=47.0333, lng=11.8667,
        height=186, year_built=1986,
        river_name_el="Ziller", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Limberg", name_el="Limberg",
        capacity_m3=85_000_000, capacity_mcm=85.0,
        lat=47.1833, lng=12.7167,
        height=120, year_built=1951,
        river_name_el="Kapruner Ache", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Mooserboden", name_el="Mooserboden",
        capacity_m3=85_000_000, capacity_mcm=85.0,
        lat=47.1500, lng=12.7167,
        height=107, year_built=1955,
        river_name_el="Kapruner Ache", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Lunersee", name_el="Lünersee",
        capacity_m3=78_000_000, capacity_mcm=78.0,
        lat=47.0500, lng=9.7500,
        height=32, year_built=1959,
        river_name_el="Ill", type_el="Steinschüttdamm",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Stausee Ottenstein", name_el="Stausee Ottenstein",
        capacity_m3=64_000_000, capacity_mcm=64.0,
        lat=48.6167, lng=15.3500,
        height=69, year_built=1957,
        river_name_el="Kamp", type_el="Gewichtsstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Durlassboden", name_el="Durlassboden",
        capacity_m3=53_000_000, capacity_mcm=53.0,
        lat=47.1333, lng=12.0833,
        height=83, year_built=1967,
        river_name_el="Gerlos", type_el="Steinschüttdamm",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kopssee", name_el="Kopssee",
        capacity_m3=43_000_000, capacity_mcm=43.0,
        lat=46.9667, lng=10.1167,
        height=122, year_built=1969,
        river_name_el="Ill", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Silvretta", name_el="Silvretta",
        capacity_m3=38_000_000, capacity_mcm=38.0,
        lat=46.8833, lng=10.0833,
        height=80, year_built=1943,
        river_name_el="Ill", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Tauernmoossee", name_el="Tauernmoossee",
        capacity_m3=13_000_000, capacity_mcm=13.0,
        lat=47.1333, lng=12.5833,
        height=28, year_built=1988,
        river_name_el="Stubache", type_el="Steinschüttdamm",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Vermunt", name_el="Vermunt",
        capacity_m3=12_000_000, capacity_mcm=12.0,
        lat=46.9167, lng=10.1000,
        height=38, year_built=1930,
        river_name_el="Ill", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Drossen", name_el="Drossen",
        capacity_m3=4_000_000, capacity_mcm=4.0,
        lat=47.2000, lng=12.7500,
        height=75, year_built=1949,
        river_name_el="Salzach", type_el="Bogenstaumauer",
        image_url="", wikipedia_url="",
    ),
]

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _AUSTRIA_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _AUSTRIA_DAMS)

# eHYD does not expose a simple parseable API endpoint for current reservoir
# levels. This URL is a placeholder — we fetch it and return 0.0 if parsing
# fails, so the scheduler can try again when better data becomes available.
_EHYD_URL = "https://ehyd.gv.at"


class AustriaProvider(BaseProvider):
    """DataProvider implementation for eHYD (Austria Federal Hydrographic Service).

    eHYD does not provide a simple JSON or parseable HTML API for reservoir
    storage levels. This provider returns hardcoded dam metadata with 0.0
    percentages. If a parseable endpoint is discovered in future, replace the
    _fetch_upstream_data stub with real parsing logic.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client)

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_AUSTRIA_DAMS)

    async def _probe_upstream(self) -> None:
        """Probe the eHYD endpoint to raise UpstreamAPIError on HTTP failures.

        Any HTTP error (5xx, network failure) is re-raised so the scheduler
        can record the failure. A 200 with unparseable content is tolerated —
        we fall back to 0.0 for all dams rather than failing noisily.
        """
        try:
            response = await self._client.get(_EHYD_URL)
        except httpx.RequestError as exc:
            raise UpstreamAPIError(f"eHYD request failed: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamAPIError(
                f"eHYD returned HTTP {response.status_code}"
            )
        # Content is not parseable in a stable way — fall through to 0.0 fallback.

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Probe upstream to surface connectivity failures; if it returns 200
        # but no parseable data, we fall back gracefully to 0.0 for all dams.
        await self._probe_upstream()
        return zero_fill_snapshot(_AUSTRIA_DAMS, _TOTAL_CAPACITY_MCM, target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        # Same probe pattern: surface HTTP errors, fall back to 0.0 otherwise.
        await self._probe_upstream()
        return zero_fill_date_statistics(_AUSTRIA_DAMS, target_date)
