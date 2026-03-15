"""
Norway data provider — fetches from NVE Magasinstatistikk API.

Upstream: https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/
Format: JSON array of weekly hydropower reservoir fill statistics.
Coverage: National aggregates split into 5 electricity price zones (NO1–NO5).

Unlike other Nero countries, Norway does NOT publish individual reservoir data.
The public API from the Norwegian Water Resources and Energy Directorate (NVE)
provides data aggregated into the same zones used by Nord Pool electricity trading:
NO1 (East), NO2 (Southwest), NO3 (Central), NO4 (North), NO5 (West).

fyllingsgrad is already in 0–1 scale matching Nero's internal storage convention,
so no conversion is needed. Capacity is provided in TWh; we convert to hm³ using
the Norwegian hydropower approximation of 850 hm³/TWh (varies slightly by region
but is a standard industry figure for Norwegian reservoirs).

If the API is unreachable or returns an unexpected response, all zones default to
0.0 rather than raising — the scheduler retries at the next sync interval.
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

# NVE API endpoint paths (relative to base_url)
_LATEST_WEEK_PATH = (
    "/magasinstatistikk/api/Magasinstatistikk/HentOffentligDataSisteUke"
)
_HISTORICAL_PATH = (
    "/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"
)

# Conversion factor: 1 TWh ≈ 850 hm³ for Norwegian hydropower reservoirs.
# This is a well-established industry approximation used by NVE publications.
_TWH_TO_HM3 = 850.0

# ── Zone metadata ────────────────────────────────────────────────────────────
# Each Norwegian electricity price zone is treated as a single "reservoir" entry.
# name_en: ASCII form used in URLs and DB (must match omrnr ordering below).
# name_el: Norwegian display name for the zone.
# Coordinates are approximate zone centroids.

_NORWAY_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="NO1-East",
        name_el="Østlandet",
        # NO1: 11.2 TWh capacity × 850 hm³/TWh ≈ 9,520 hm³
        capacity_mcm=9_520.0,
        capacity_m3=int(9_520.0 * 1_000_000),
        lat=60.0,
        lng=11.0,
        height=0,
        year_built=0,
        river_name_el="Glåma/Drammensvassdraget",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="NO2-Southwest",
        name_el="Sørlandet/Vestlandet",
        # NO2: 33.5 TWh × 850 ≈ 28,475 hm³
        capacity_mcm=28_475.0,
        capacity_m3=int(28_475.0 * 1_000_000),
        lat=59.0,
        lng=6.5,
        height=0,
        year_built=0,
        river_name_el="Otra/Ulla-Førre",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="NO3-Central",
        name_el="Midt-Norge",
        # NO3: 10.1 TWh × 850 ≈ 8,585 hm³
        capacity_mcm=8_585.0,
        capacity_m3=int(8_585.0 * 1_000_000),
        lat=63.0,
        lng=10.0,
        height=0,
        year_built=0,
        river_name_el="Orkla/Nea",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="NO4-North",
        name_el="Nord-Norge",
        # NO4: 18.3 TWh × 850 ≈ 15,555 hm³
        capacity_mcm=15_555.0,
        capacity_m3=int(15_555.0 * 1_000_000),
        lat=69.0,
        lng=19.0,
        height=0,
        year_built=0,
        river_name_el="Alta/Altaelva",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="NO5-West",
        name_el="Vestlandet",
        # NO5: 14.8 TWh × 850 ≈ 12,580 hm³
        capacity_mcm=12_580.0,
        capacity_m3=int(12_580.0 * 1_000_000),
        lat=61.0,
        lng=6.5,
        height=0,
        year_built=0,
        river_name_el="Sira-Kvina/Lyse",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
]

# Map omrnr (1–5) → name_en for fast lookup when parsing API records
_OMRNR_TO_NAME: dict[int, str] = {
    1: "NO1-East",
    2: "NO2-Southwest",
    3: "NO3-Central",
    4: "NO4-North",
    5: "NO5-West",
}

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _NORWAY_DAMS)


def _zero_fill_snapshot(target_date: date) -> PercentageSnapshot:
    """Return an all-zeros snapshot for all 5 zones. Used on API failure."""
    return PercentageSnapshot(
        date=target_date,
        dam_percentages=[
            DamPercentage(dam_name_en=d.name_en, percentage=0.0)
            for d in _NORWAY_DAMS
        ],
        total_percentage=0.0,
        total_capacity_mcm=_TOTAL_CAPACITY_MCM,
    )


def _zero_fill_date_statistics(target_date: date) -> DateStatistics:
    """Return zero-fill date statistics for all 5 zones. Used on API failure."""
    return DateStatistics(
        date=target_date,
        dam_statistics=[
            DamStatistic(dam_name_en=d.name_en, storage_mcm=0.0, inflow_mcm=0.0)
            for d in _NORWAY_DAMS
        ],
    )


class NorwayProvider:
    """DataProvider implementation for NVE Magasinstatistikk weekly reservoir data.

    Fetches the latest weekly fill percentages for Norway's 5 electricity price
    zones. The NVE API returns zone-aggregated data because individual reservoir
    data is commercially sensitive. fyllingsgrad (fill ratio 0–1) is used
    directly as Nero's internal percentage. On any API error, all zones default
    to 0.0 — the scheduler will retry at the next sync interval.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_NORWAY_DAMS)

    async def _fetch_latest_json(self) -> list[dict[str, Any]] | None:
        """Fetch the latest weekly data from NVE. Returns None on any error."""
        try:
            response = await self._client.get(_LATEST_WEEK_PATH)
        except httpx.RequestError as exc:
            logger.warning("NVE request failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning("NVE returned HTTP %d", response.status_code)
            return None

        try:
            data: list[dict[str, Any]] = response.json()
            return data
        except Exception as exc:
            logger.warning("Failed to parse NVE JSON: %s", exc)
            return None

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        data = await self._fetch_latest_json()
        if data is None:
            return _zero_fill_snapshot(target_date)

        # Filter to EL zone records only; omrType="NO" is the national aggregate
        el_records: dict[int, float] = {}
        for record in data:
            if record.get("omrType") != "EL":
                continue
            omrnr = record.get("omrnr")
            fyllingsgrad = record.get("fyllingsgrad")
            if omrnr is None or fyllingsgrad is None:
                continue
            try:
                el_records[int(omrnr)] = float(fyllingsgrad)
            except (TypeError, ValueError) as exc:
                logger.warning("Unexpected NVE record values: %s", exc)

        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0

        for dam in _NORWAY_DAMS:
            omrnr = next(
                (k for k, v in _OMRNR_TO_NAME.items() if v == dam.name_en), None
            )
            pct = el_records.get(omrnr, 0.0) if omrnr is not None else 0.0
            # Clamp to [0, 1] — API values should already be in range, but guard
            pct = max(0.0, min(1.0, pct))
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
        data = await self._fetch_latest_json()
        if data is None:
            return _zero_fill_date_statistics(target_date)

        # Build a map of omrnr → fylling_TWh for storage_mcm calculation
        el_twh: dict[int, float] = {}
        for record in data:
            if record.get("omrType") != "EL":
                continue
            omrnr = record.get("omrnr")
            fylling_twh = record.get("fylling_TWh")
            if omrnr is None or fylling_twh is None:
                continue
            try:
                el_twh[int(omrnr)] = float(fylling_twh)
            except (TypeError, ValueError) as exc:
                logger.warning("Unexpected NVE fylling_TWh value: %s", exc)

        dam_statistics: list[DamStatistic] = []
        for dam in _NORWAY_DAMS:
            omrnr = next(
                (k for k, v in _OMRNR_TO_NAME.items() if v == dam.name_en), None
            )
            twh = el_twh.get(omrnr, 0.0) if omrnr is not None else 0.0
            # Convert TWh → hm³ using the Norwegian hydropower approximation
            storage_mcm = twh * _TWH_TO_HM3
            dam_statistics.append(
                DamStatistic(
                    dam_name_en=dam.name_en,
                    storage_mcm=storage_mcm,
                    inflow_mcm=0.0,
                )
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        """Fetch 30 years of weekly historical data from NVE's bulk endpoint.

        HentOffentligData returns ~1,000+ records covering 1995-present in a
        single unauthenticated GET. Each record represents one week × one zone.
        We group by date, build a PercentageSnapshot per date, and sort ascending
        so the caller can feed the list directly into the timeseries DB writer.
        """
        try:
            response = await self._client.get(_HISTORICAL_PATH)
        except httpx.RequestError as exc:
            logger.warning("NVE historical request failed: %s", exc)
            return []

        if response.status_code != 200:
            logger.warning("NVE historical endpoint returned HTTP %d", response.status_code)
            return []

        try:
            data: list[dict[str, Any]] = response.json()
        except Exception as exc:
            logger.warning("Failed to parse NVE historical JSON: %s", exc)
            return []

        # Group EL-zone records by date string; discard national (NO) aggregates
        by_date: dict[str, dict[int, float]] = {}
        for record in data:
            if record.get("omrType") != "EL":
                continue
            dato_id = record.get("dato_Id")
            omrnr = record.get("omrnr")
            fyllingsgrad = record.get("fyllingsgrad")
            if dato_id is None or omrnr is None or fyllingsgrad is None:
                continue
            try:
                by_date.setdefault(str(dato_id), {})[int(omrnr)] = float(fyllingsgrad)
            except (TypeError, ValueError) as exc:
                logger.warning("Unexpected NVE historical record values: %s", exc)

        snapshots: list[PercentageSnapshot] = []
        for dato_id in sorted(by_date):
            try:
                snapshot_date = date.fromisoformat(dato_id)
            except ValueError:
                logger.warning("Skipping unparseable NVE date: %s", dato_id)
                continue

            zone_map = by_date[dato_id]
            dam_percentages: list[DamPercentage] = []
            total_volume_mcm = 0.0

            for dam in _NORWAY_DAMS:
                omrnr = next(
                    (k for k, v in _OMRNR_TO_NAME.items() if v == dam.name_en), None
                )
                pct = zone_map.get(omrnr, 0.0) if omrnr is not None else 0.0
                pct = max(0.0, min(1.0, pct))
                dam_percentages.append(
                    DamPercentage(dam_name_en=dam.name_en, percentage=pct)
                )
                total_volume_mcm += pct * dam.capacity_mcm

            total_pct = (
                total_volume_mcm / _TOTAL_CAPACITY_MCM
                if _TOTAL_CAPACITY_MCM > 0
                else 0.0
            )
            snapshots.append(
                PercentageSnapshot(
                    date=snapshot_date,
                    dam_percentages=dam_percentages,
                    total_percentage=total_pct,
                    total_capacity_mcm=_TOTAL_CAPACITY_MCM,
                )
            )

        return snapshots

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(
        self, date_from: date, date_until: date
    ) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
