"""
Finland data provider — fetches from SYKE (Finnish Environment Institute) OData API.

Upstream: https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.1/
Format: OData JSON (the XML/Atom format returns HTTP 400)
Coverage: ~5,000 monitoring stations with daily water level data (cm).

Finnish "reservoirs" are mostly regulated natural lakes, some of the largest
water bodies in Northern Europe. The API provides water level in cm above a
station-local gauge zero point (datum); values vary enormously between stations
(e.g. Saimaa ~309 cm, Lokka ~24302 cm) because each station uses a different
local datum offset — the numbers are NOT comparable between lakes.

For MVP we treat any positive reading as a proxy for a healthy lake and map it
to 0.70 (70%). If the API is unreachable or parsing fails the provider returns
zero-fill defaults rather than raising — the scheduler retries on the next cycle.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

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

# ── Hardcoded lake/reservoir metadata ────────────────────────────────────────
# Finnish regulated lakes listed by descending capacity.
# name_en: ASCII form used in URLs; name_el: Finnish form used for display.
# Capacities in hm³ (= MCM). Heights are 0 for natural regulated lakes.

_FINLAND_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Inarijarvi", name_el="Inarijärvi",
        capacity_m3=15_000_000_000, capacity_mcm=15000.0,
        lat=69.1, lng=27.5,
        height=0, year_built=1942,
        river_name_el="Ivalojoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Saimaa", name_el="Saimaa",
        capacity_m3=9_000_000_000, capacity_mcm=9000.0,
        lat=61.2, lng=28.5,
        height=0, year_built=1896,
        river_name_el="Vuoksi", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Paijanne", name_el="Päijänne",
        capacity_m3=4_000_000_000, capacity_mcm=4000.0,
        lat=61.5, lng=25.5,
        height=0, year_built=1964,
        river_name_el="Kymijoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Oulujarvi", name_el="Oulujärvi",
        capacity_m3=2_500_000_000, capacity_mcm=2500.0,
        lat=64.3, lng=27.2,
        height=0, year_built=1951,
        river_name_el="Oulujoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Lokka", name_el="Lokka",
        capacity_m3=1_400_000_000, capacity_mcm=1400.0,
        lat=67.8, lng=27.7,
        height=11, year_built=1967,
        river_name_el="Luiro", type_el="Tekojärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Porttipahta", name_el="Porttipahta",
        capacity_m3=1_350_000_000, capacity_mcm=1350.0,
        lat=67.4, lng=26.6,
        height=35, year_built=1970,
        river_name_el="Kemijoki", type_el="Tekojärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Pielinen", name_el="Pielinen",
        capacity_m3=1_100_000_000, capacity_mcm=1100.0,
        lat=63.2, lng=29.5,
        height=0, year_built=1970,
        river_name_el="Pielisjoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kemijarvi", name_el="Kemijärvi",
        capacity_m3=850_000_000, capacity_mcm=850.0,
        lat=66.7, lng=27.2,
        height=0, year_built=1965,
        river_name_el="Kemijoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nasijarvi", name_el="Näsijärvi",
        capacity_m3=320_000_000, capacity_mcm=320.0,
        lat=61.6, lng=23.8,
        height=0, year_built=1872,
        river_name_el="Nokianvirta", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Pyhajarvi", name_el="Pyhäjärvi",
        capacity_m3=250_000_000, capacity_mcm=250.0,
        lat=61.0, lng=22.3,
        height=0, year_built=1958,
        river_name_el="Eurajoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ontojarvi", name_el="Ontojärvi",
        capacity_m3=250_000_000, capacity_mcm=250.0,
        lat=64.1, lng=28.5,
        height=0, year_built=1951,
        river_name_el="Ontojoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nuasjarvi", name_el="Nuasjärvi",
        capacity_m3=200_000_000, capacity_mcm=200.0,
        lat=64.1, lng=28.0,
        height=0, year_built=1951,
        river_name_el="Oulujoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kiantajarvi", name_el="Kiantajärvi",
        capacity_m3=430_000_000, capacity_mcm=430.0,
        lat=64.4, lng=28.8,
        height=0, year_built=1964,
        river_name_el="Emäjoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Vuokkijarvi", name_el="Vuokkijärvi",
        capacity_m3=170_000_000, capacity_mcm=170.0,
        lat=64.2, lng=29.0,
        height=0, year_built=1964,
        river_name_el="Vuokkijoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Koitere", name_el="Koitere",
        capacity_m3=170_000_000, capacity_mcm=170.0,
        lat=63.0, lng=30.5,
        height=0, year_built=1955,
        river_name_el="Koitajoki", type_el="Säännöstelty luonnonjärvi",
        image_url="", wikipedia_url="",
    ),
]

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _FINLAND_DAMS)

# SYKE station IDs (Paikka_Id) for each lake — verified against live API 2026-03-14.
# These are required for the per-lake Vedenkorkeus query; without them the API
# returns data for an arbitrary station rather than the correct lake.
_STATION_IDS: dict[str, int] = {
    "Inarijarvi":   2562,
    "Saimaa":       1898,
    "Paijanne":     1998,
    "Oulujarvi":    2405,
    "Lokka":        2468,
    "Porttipahta":  2458,
    "Pielinen":     1749,
    "Kemijarvi":    2475,
    "Nasijarvi":    2226,
    "Pyhajarvi":    2168,
    "Ontojarvi":    2394,
    "Nuasjarvi":    2400,
    "Kiantajarvi":  2372,
    "Vuokkijarvi":  2375,
    "Koitere":      1770,
}

# SYKE OData base URL — HTTPS required (HTTP returns 400 for OData endpoints)
_SYKE_API_BASE = "https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.1"


def _parse_syke_json(json_data: dict[str, Any]) -> float | None:
    """Extract the first Arvo value from a SYKE OData JSON response.

    Returns the water level in cm, or None if no value is found.
    The API can return an empty value array when a station has no recent data.
    """
    value_list = json_data.get("value", [])
    if not value_list:
        return None
    first = value_list[0]
    raw = first.get("Arvo")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning("Unexpected non-numeric Arvo value: %r", raw)
        return None


def _water_level_to_percentage(level_cm: float, capacity_mcm: float) -> float:
    """Convert a raw water level observation to an approximate fill percentage.

    Finnish regulated lakes report water level in cm above a station-local gauge
    zero point, not as a percentage. The values are not comparable between lakes
    because each uses a different datum offset. Without per-lake regulation
    boundary data this conversion is approximate: we treat any valid API
    observation as a proxy for a healthy lake and map it to 0.70 (70%) as a
    reasonable mid-range estimate. Future improvement: fetch regulation
    boundaries from /api/jarvirajapinta/1.1/ and compute a true fill ratio.
    """
    # Ignore unused parameter — placeholder for future improvement
    _ = capacity_mcm
    # Any positive water level reading → treat as 70% full (healthy mid-range)
    return 0.70 if level_cm > 0 else 0.0


class FinlandProvider:
    """DataProvider implementation for SYKE Finnish hydrology OData API.

    Fetches current water level readings for Finland's 15 largest regulated
    lakes. Each lake is queried individually by its Paikka_Id station ID to
    ensure station-specific data rather than a generic sample. Because SYKE
    reports water level (cm above datum) rather than fill percentage,
    approximate percentages are computed via _water_level_to_percentage(). If
    the API is unavailable, all percentages default to 0.0 — the scheduler
    will retry at the next sync interval.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_FINLAND_DAMS)

    async def _fetch_level_for_dam(self, dam: DamInfo) -> float:
        """Fetch the latest water level (cm) for a specific dam from SYKE OData.

        Queries by Paikka_Id so we get data for the correct monitoring station.
        Returns 0.0 on any error so that a single failing station doesn't abort
        the whole sync.
        """
        station_id = _STATION_IDS.get(dam.name_en)
        if station_id is None:
            logger.warning("No station ID mapped for %s — skipping", dam.name_en)
            return 0.0

        url = f"{_SYKE_API_BASE}/odata/Vedenkorkeus"
        params = {
            "$filter": f"Paikka_Id eq {station_id}",
            "$orderby": "Aika desc",
            "$top": "1",
        }
        try:
            response = await self._client.get(url, params=params)
        except httpx.RequestError as exc:
            logger.warning("SYKE request failed for %s: %s", dam.name_en, exc)
            return 0.0

        if response.status_code != 200:
            logger.warning(
                "SYKE returned HTTP %d for %s", response.status_code, dam.name_en
            )
            return 0.0

        try:
            json_data: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("Failed to parse SYKE JSON for %s: %s", dam.name_en, exc)
            return 0.0

        level = _parse_syke_json(json_data)
        return level if level is not None else 0.0

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0

        for dam in _FINLAND_DAMS:
            level_cm = await self._fetch_level_for_dam(dam)
            pct = _water_level_to_percentage(level_cm, dam.capacity_mcm)
            dam_percentages.append(DamPercentage(dam_name_en=dam.name_en, percentage=pct))
            total_volume_mcm += pct * dam.capacity_mcm

        total_pct = (
            total_volume_mcm / _TOTAL_CAPACITY_MCM if _TOTAL_CAPACITY_MCM > 0 else 0.0
        )

        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=total_pct,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        dam_statistics: list[DamStatistic] = []
        for dam in _FINLAND_DAMS:
            level_cm = await self._fetch_level_for_dam(dam)
            pct = _water_level_to_percentage(level_cm, dam.capacity_mcm)
            storage_mcm = pct * dam.capacity_mcm
            dam_statistics.append(
                DamStatistic(
                    dam_name_en=dam.name_en,
                    storage_mcm=storage_mcm,
                    inflow_mcm=0.0,
                )
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        # SYKE historical data is not consumed in MVP; incremental sync builds
        # the timeseries over time via the scheduler.
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
