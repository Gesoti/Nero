"""
Italy data provider — fetches from OpenData Sicilia GitHub CSV.

Upstream: opendatasicilia/emergenza-idrica-sicilia (GitHub raw CSV)
Covers Sicily's 13 largest reservoirs managed by the Sicilian Basin Authority.
Data is sourced from a community project that extracts data from official PDF reports.
Updates are typically daily, though lag varies with PDF publication schedule.

Daily CSV columns: nome_diga, data, volume_autorizzato_mc, volume_invasato_mc
  Volumes are in cubic metres (m³). Divide by 1_000_000 to get hm³ (= MCM).

Historical monthly CSV columns: cod, diga, data, volume
  Volumes are already in hm³ (no conversion needed).
  Date range: December 2016 – present (~9 years, ~8,400 rows, 29 dams).
"""
from __future__ import annotations

import collections
import csv
import io
import logging
from datetime import date, datetime

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
# 13 Sicilian reservoirs. name_en is ASCII-safe for URL paths.
# name_el holds the Italian name (used in the UI's detail page subtitle).
# Capacities verified against the authorised volumes (volume_autorizzato_mc) in
# the OpenData Sicilia dataset and cross-referenced with SIAS/Regione Siciliana data.

_ITALY_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Ancipa", name_el="Ancipa",
        capacity_m3=30_400_000, capacity_mcm=30.4,
        lat=37.7833, lng=14.5667,
        height=105, year_built=1953,
        river_name_el="Troina", type_el="Gravità",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Pozzillo", name_el="Pozzillo",
        capacity_m3=150_000_000, capacity_mcm=150.0,
        lat=37.7833, lng=14.6333,
        height=56, year_built=1959,
        river_name_el="Salso", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ogliastro", name_el="Ogliastro",
        capacity_m3=110_000_000, capacity_mcm=110.0,
        lat=37.5500, lng=14.1167,
        height=60, year_built=1986,
        river_name_el="Imera Meridionale", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Prizzi", name_el="Prizzi",
        capacity_m3=10_000_000, capacity_mcm=10.0,
        lat=37.7167, lng=13.4333,
        height=50, year_built=1975,
        river_name_el="Sosio", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Fanaco", name_el="Fanaco",
        capacity_m3=21_000_000, capacity_mcm=21.0,
        lat=37.6333, lng=13.5667,
        height=68, year_built=1981,
        river_name_el="Platani", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Gammauta", name_el="Gammauta",
        capacity_m3=7_000_000, capacity_mcm=7.0,
        lat=37.6000, lng=13.3333,
        height=50, year_built=1964,
        river_name_el="affluente Magazzolo", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Leone", name_el="Leone",
        capacity_m3=7_000_000, capacity_mcm=7.0,
        lat=37.7833, lng=13.0833,
        height=45, year_built=1971,
        river_name_el="affluente Belice", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Garcia", name_el="Garcia",
        capacity_m3=64_000_000, capacity_mcm=64.0,
        lat=37.8000, lng=13.1333,
        height=51, year_built=1990,
        river_name_el="Belice", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Piana degli Albanesi", name_el="Piana degli Albanesi",
        capacity_m3=31_000_000, capacity_mcm=31.0,
        lat=37.9500, lng=13.2667,
        height=50, year_built=1923,
        river_name_el="affluente Belice", type_el="Gravità",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Scanzano", name_el="Scanzano",
        capacity_m3=2_600_000, capacity_mcm=2.6,
        lat=38.0167, lng=13.4333,
        height=25, year_built=1931,
        river_name_el="Eleuterio", type_el="Gravità",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Rosamarina", name_el="Rosamarina",
        capacity_m3=100_000_000, capacity_mcm=100.0,
        lat=37.9333, lng=13.5500,
        height=75, year_built=1996,
        river_name_el="San Leonardo", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Cimia", name_el="Cimia",
        capacity_m3=12_000_000, capacity_mcm=12.0,
        lat=37.0833, lng=14.5833,
        height=55, year_built=1977,
        river_name_el="Dirillo", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ragoleto", name_el="Ragoleto",
        capacity_m3=2_500_000, capacity_mcm=2.5,
        lat=37.0333, lng=14.6000,
        height=30, year_built=1965,
        river_name_el="affluente Dirillo", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
]

# Map name_en → upstream CSV "nome_diga" field (as it appears in the CSV).
# The CSV uses Italian dam names; some match our name_en exactly, others differ.
_UPSTREAM_NAME_MAP: dict[str, str] = {
    "Ancipa": "Ancipa",
    "Pozzillo": "Pozzillo",
    "Ogliastro": "Ogliastro",
    "Prizzi": "Prizzi",
    "Fanaco": "Fanaco",
    "Gammauta": "Gammauta",
    "Leone": "Leone",
    "Garcia": "Garcia",
    "Piana degli Albanesi": "Piana degli Albanesi",
    "Scanzano": "Scanzano",
    "Rosamarina": "Rosamarina",
    "Cimia": "Cimia",
    "Ragoleto": "Ragoleto",
}

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _ITALY_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _ITALY_DAMS)

# Raw CSV URL from the OpenData Sicilia GitHub repository.
# Using the "latest" file which holds the most recent observation for each dam.
_CSV_URL = (
    "https://raw.githubusercontent.com/opendatasicilia/emergenza-idrica-sicilia"
    "/refs/heads/main/risorse/sicilia_dighe_volumi_giornalieri_latest.csv"
)

# Historical monthly CSV — December 2016 to present, 29 dams, volumes in hm³.
# We filter to only the 13 dams we track.  Names in this CSV may differ slightly
# from _UPSTREAM_NAME_MAP — this map normalises them to our name_en keys.
_HISTORICAL_CSV_URL = (
    "https://raw.githubusercontent.com/opendatasicilia/emergenza-idrica-sicilia"
    "/refs/heads/main/risorse/sicilia_dighe_volumi.csv"
)

# Maps the monthly CSV's "diga" column value → our tracked name_en.
# All 13 tracked dams have identical names in both CSVs, so this is a 1:1 mapping.
# Untracked dams (the other 16 out of 29) simply won't appear in this dict and
# will be skipped during timeseries parsing.
_HISTORICAL_NAME_MAP: dict[str, str] = {
    "Ancipa": "Ancipa",
    "Pozzillo": "Pozzillo",
    "Ogliastro": "Ogliastro",
    "Prizzi": "Prizzi",
    "Fanaco": "Fanaco",
    "Gammauta": "Gammauta",
    "Leone": "Leone",
    "Garcia": "Garcia",
    "Piana degli Albanesi": "Piana degli Albanesi",
    "Scanzano": "Scanzano",
    "Rosamarina": "Rosamarina",
    "Cimia": "Cimia",
    "Ragoleto": "Ragoleto",
}


def _parse_it_volume_mc(raw: str) -> float:
    """Parse volume in cubic metres from CSV string; return as hm³ (MCM).

    OpenData Sicilia stores volumes in m³ (e.g. '30400000').
    We divide by 1_000_000 to convert to hm³ which is the unit used throughout
    this app (= MCM = million cubic metres).
    """
    return float(raw.strip()) / 1_000_000.0


def _parse_csv(text: str) -> dict[str, dict[str, str]]:
    """Parse the raw CSV text and return a dict keyed by 'nome_diga'.

    Returns the latest row for each dam name (the 'latest' CSV should have
    one row per dam, but if multiple rows exist we take the last one).
    """
    result: dict[str, dict[str, str]] = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        nome = row.get("nome_diga", "").strip()
        if nome:
            result[nome] = {k: v.strip() for k, v in row.items()}
    return result


class ItalyProvider:
    """DataProvider implementation for OpenData Sicilia CSV (Sicily reservoir data)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        # Cache CSV data within a single sync cycle to avoid re-fetching for
        # both fetch_percentages and fetch_date_statistics calls.
        self._cached_rows: dict[str, dict[str, str]] | None = None

    def _clear_cache(self) -> None:
        self._cached_rows = None

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_ITALY_DAMS)

    async def _fetch_csv_data(self) -> dict[str, dict[str, str]]:
        """Fetch the latest CSV from GitHub and return rows keyed by dam name."""
        if self._cached_rows is not None:
            return self._cached_rows

        try:
            response = await self._client.get(_CSV_URL)
        except httpx.RequestError as exc:
            raise UpstreamAPIError(f"OpenData Sicilia request failed: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamAPIError(
                f"OpenData Sicilia returned HTTP {response.status_code}"
            )

        self._cached_rows = _parse_csv(response.text)
        return self._cached_rows

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        rows = await self._fetch_csv_data()

        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0

        for dam in _ITALY_DAMS:
            upstream_name = _UPSTREAM_NAME_MAP.get(dam.name_en, dam.name_en)
            row = rows.get(upstream_name)

            pct = 0.0
            volume_mcm = 0.0

            if row:
                autorizzato_raw = row.get("volume_autorizzato_mc", "")
                invasato_raw = row.get("volume_invasato_mc", "")
                if autorizzato_raw and invasato_raw:
                    try:
                        autorizzato = float(autorizzato_raw)
                        invasato = float(invasato_raw)
                        if autorizzato > 0:
                            pct = invasato / autorizzato
                        volume_mcm = _parse_it_volume_mc(invasato_raw)
                    except (ValueError, ZeroDivisionError) as exc:
                        logger.warning("Failed to parse volume for %s: %s", dam.name_en, exc)

            dam_percentages.append(DamPercentage(dam_name_en=dam.name_en, percentage=pct))
            total_volume_mcm += volume_mcm

        total_pct = (
            total_volume_mcm / _TOTAL_CAPACITY_MCM
            if _TOTAL_CAPACITY_MCM > 0
            else 0.0
        )

        self._clear_cache()

        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=total_pct,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        rows = await self._fetch_csv_data()

        dam_statistics: list[DamStatistic] = []

        for dam in _ITALY_DAMS:
            upstream_name = _UPSTREAM_NAME_MAP.get(dam.name_en, dam.name_en)
            row = rows.get(upstream_name)

            storage_mcm = 0.0
            if row:
                invasato_raw = row.get("volume_invasato_mc", "")
                if invasato_raw:
                    try:
                        storage_mcm = _parse_it_volume_mc(invasato_raw)
                    except ValueError as exc:
                        logger.warning("Failed to parse storage for %s: %s", dam.name_en, exc)

            dam_statistics.append(
                DamStatistic(
                    dam_name_en=dam.name_en,
                    storage_mcm=storage_mcm,
                    inflow_mcm=0.0,
                )
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        """Fetch ~9 years of monthly historical data from the OpenData Sicilia archive.

        The historical CSV has columns: cod, diga, data, volume (hm³).
        We aggregate per date, calculate per-dam and total percentages, and return
        one PercentageSnapshot per unique date, sorted ascending.

        Returns [] on any HTTP or network error so the caller can continue with
        whatever data is already in the local database.
        """
        try:
            response = await self._client.get(_HISTORICAL_CSV_URL)
        except httpx.RequestError as exc:
            logger.warning("Historical timeseries request failed: %s", exc)
            return []

        if response.status_code != 200:
            logger.warning(
                "Historical timeseries returned HTTP %s", response.status_code
            )
            return []

        # Group rows by date string first, then build one snapshot per date.
        # Using defaultdict(dict) keyed as: date_str → {name_en: volume_hm3}
        by_date: dict[str, dict[str, float]] = collections.defaultdict(dict)

        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            diga = row.get("diga", "").strip()
            name_en = _HISTORICAL_NAME_MAP.get(diga)
            if name_en is None:
                # Not one of our 13 tracked dams — skip.
                continue

            raw_date = row.get("data", "").strip()
            raw_volume = row.get("volume", "").strip()
            if not raw_date or not raw_volume:
                continue

            try:
                volume_hm3 = float(raw_volume)
                # Validate the date is parseable; store as string for dict key.
                datetime.strptime(raw_date, "%Y-%m-%d")
            except ValueError as exc:
                logger.warning("Skipping row with bad date/volume (%s): %s", row, exc)
                continue

            by_date[raw_date][name_en] = volume_hm3

        snapshots: list[PercentageSnapshot] = []
        for date_str, dam_volumes in by_date.items():
            snapshot_date = date.fromisoformat(date_str)

            dam_percentages: list[DamPercentage] = []
            total_volume_hm3 = 0.0

            for dam in _ITALY_DAMS:
                volume_hm3 = dam_volumes.get(dam.name_en, 0.0)
                # Cap at 1.0 — overfill readings occasionally appear in the source data.
                pct = min(volume_hm3 / dam.capacity_mcm, 1.0) if dam.capacity_mcm > 0 else 0.0
                dam_percentages.append(DamPercentage(dam_name_en=dam.name_en, percentage=pct))
                total_volume_hm3 += volume_hm3

            total_pct = (
                min(total_volume_hm3 / _TOTAL_CAPACITY_MCM, 1.0)
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

        return sorted(snapshots, key=lambda s: s.date)

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        return []

    async def fetch_events(
        self, date_from: date, date_until: date
    ) -> list[WaterEvent]:
        return []

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
