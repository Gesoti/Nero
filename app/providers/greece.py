"""
Greece data provider — fetches from the EYDAP OpenData API.

Upstream: opendata-api-eydap.growthfund.gr
Covers 4 reservoirs serving Attica (Athens metro area, ~3.7M people):
Mornos, Yliki, Evinos, Marathon.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

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

# EYDAP API response field → our dam name_en
_EYDAP_FIELD_MAP: dict[str, str] = {
    "Eyinos": "Evinos",
    "Marathonas": "Marathon",
    "Mornos": "Mornos",
    "Yliko": "Yliki",
}

# Lookup capacity by dam name_en for percentage derivation
_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _GREECE_DAMS}

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _GREECE_DAMS)

_EYDAP_BASE_URL = "https://opendata-api-eydap.growthfund.gr"


def _parse_eydap_volume(raw: str) -> int:
    """Convert EYDAP European-format number string to integer m³.

    EYDAP uses dots as thousands separators: "93.063.000" → 93063000.
    A plain integer string is also accepted.
    """
    return int(raw.strip().replace(".", ""))


class GreeceProvider:
    """DataProvider implementation for the EYDAP OpenData API (Athens water supply)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_GREECE_DAMS)

    async def _fetch_savings(self, target_date: date) -> dict[str, str]:
        """Call GET /api/Savings/Day/{DD-MM-YYYY} and return the raw JSON dict.

        The EYDAP API returns a JSON list of dicts (one per day, sometimes
        including the day before). We take the last element which corresponds
        to the requested date.
        """
        date_str = target_date.strftime("%d-%m-%Y")
        url = f"{_EYDAP_BASE_URL}/api/Savings/Day/{date_str}"
        try:
            response = await self._client.get(url)
        except httpx.RequestError as exc:
            raise UpstreamAPIError(f"EYDAP request failed: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamAPIError(
                f"EYDAP returned HTTP {response.status_code} for {date_str}"
            )

        payload = response.json()
        if isinstance(payload, list):
            if not payload:
                raise UpstreamAPIError(f"EYDAP returned empty list for {date_str}")
            return payload[-1]  # type: ignore[no-any-return]
        return payload  # type: ignore[no-any-return]

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        data = await self._fetch_savings(target_date)

        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0

        for api_field, dam_name in _EYDAP_FIELD_MAP.items():
            raw = data.get(api_field) or "0"
            volume_m3 = _parse_eydap_volume(raw)
            volume_mcm = volume_m3 / 1_000_000
            capacity_mcm = _CAPACITY_MAP[dam_name]
            pct = volume_mcm / capacity_mcm if capacity_mcm > 0 else 0.0
            dam_percentages.append(DamPercentage(dam_name_en=dam_name, percentage=pct))
            total_volume_mcm += volume_mcm

        total_pct = total_volume_mcm / _TOTAL_CAPACITY_MCM if _TOTAL_CAPACITY_MCM > 0 else 0.0

        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=total_pct,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        data = await self._fetch_savings(target_date)

        dam_statistics: list[DamStatistic] = []
        for api_field, dam_name in _EYDAP_FIELD_MAP.items():
            raw = data.get(api_field) or "0"
            volume_m3 = _parse_eydap_volume(raw)
            storage_mcm = volume_m3 / 1_000_000
            # EYDAP does not publish inflow figures via this endpoint
            dam_statistics.append(
                DamStatistic(dam_name_en=dam_name, storage_mcm=storage_mcm, inflow_mcm=0.0)
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        """Fetch daily snapshots for recent years by sampling the first day of each month.

        EYDAP's /api/Savings/Year/{date} returns a single-day aggregate, not an array,
        so we sample monthly to build a usable timeseries without hammering the API.
        """
        snapshots: list[PercentageSnapshot] = []
        today = date.today()

        # Build a list of first-of-month dates from 2020-01 to last month
        sample_dates: list[date] = []
        d = date(2020, 1, 1)
        while d < today:
            sample_dates.append(d)
            # Advance to first day of next month
            if d.month == 12:
                d = date(d.year + 1, 1, 1)
            else:
                d = date(d.year, d.month + 1, 1)

        for sample_date in sample_dates:
            try:
                snapshot = await self.fetch_percentages(sample_date)
                snapshots.append(snapshot)
            except UpstreamAPIError as exc:
                # Log and skip missing data points rather than failing the whole series
                logger.warning("EYDAP timeseries: skipping %s — %s", sample_date, exc)

        return snapshots

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(self, date_from: date, date_until: date) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
