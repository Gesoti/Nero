"""
Switzerland data provider — fetches from BFE/SFOE OGD CSV dataset.

Upstream: https://uvek-gis.admin.ch/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv
Format: CSV with weekly hydropower reservoir fill statistics by region.
Coverage: 4 linguistic/geographic regions + national total (TotalCH excluded here).

Switzerland does NOT publish individual reservoir data in a freely accessible
national dataset. The Swiss Federal Office of Energy (BFE / Bundesamt für Energie)
publishes fill levels aggregated into 4 regions that broadly correspond to Alpine
hydropower geography:
  - Wallis (Valais): the dominant canton for Swiss hydropower
  - Graubuenden (Grisons): eastern Alpine catchments
  - Tessin (Ticino): southern Alpine, drains to the Po
  - UebrigCH (Rest of Switzerland): remaining cantons

Units in the CSV are GWh (energy equivalent of stored water). We convert to hm³
using the Swiss hydro approximation of 0.85 hm³/GWh (varies by head and efficiency
but is a standard published figure for Swiss Alpine reservoirs).

The CSV has ~1,358 rows covering 2000-01-03 to present. Both fetch_percentages()
and fetch_date_statistics() use the last row (most recent weekly entry).
fetch_timeseries() parses every row to build the full historical series.

If the CSV endpoint is unreachable or returns an unexpected response, all regions
default to 0.0 rather than raising — the scheduler retries at the next interval.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date

import httpx

from app.providers.base import (
    BaseProvider,
    DamInfo,
    DamPercentage,
    DamStatistic,
    DateStatistics,
    PercentageSnapshot,
    zero_fill_date_statistics,
    zero_fill_snapshot,
)

logger = logging.getLogger(__name__)

# BFE OGD CSV path (relative to base_url)
_CSV_PATH = "/BFE/ogd/17/ogd17_fuellungsgrad_speicherseen.csv"

# Conversion factor: 1 GWh ≈ 0.85 hm³ for Swiss Alpine hydropower reservoirs.
# Source: BFE technical documentation for Speicherseen-Statistik.
_GWH_TO_HM3 = 0.85

# Column name pairs: (current_gwh_col, max_gwh_col, name_en)
# Ordered to match the expected dam list.
_REGION_COLUMNS: list[tuple[str, str, str]] = [
    ("Wallis_speicherinhalt_gwh", "Wallis_max_speicherinhalt_gwh", "Wallis"),
    ("Graubuenden_speicherinhalt_gwh", "Graubuenden_max_speicherinhalt_gwh", "Graubuenden"),
    ("Tessin_speicherinhalt_gwh", "Tessin_max_speicherinhalt_gwh", "Tessin"),
    ("UebrigCH_speicherinhalt_gwh", "UebrigCH_max_speicherinhalt_gwh", "UebrigCH"),
]

# ── Region metadata ───────────────────────────────────────────────────────────
# Each Swiss region is treated as a single "reservoir" entry. Coordinates are
# approximate centroids of the hydropower-relevant areas.
# Capacity: rough published BFE figures converted from GWh to hm³ via _GWH_TO_HM3.

_SWITZERLAND_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Wallis",
        name_el="Wallis (Valais)",
        # ~4,300 GWh × 0.85 ≈ 3,655 hm³
        capacity_mcm=3_655.0,
        capacity_m3=int(3_655.0 * 1_000_000),
        lat=46.2,
        lng=7.6,
        height=0,
        year_built=0,
        river_name_el="Rhone/Rhône",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="Graubuenden",
        name_el="Graubünden",
        # ~2,100 GWh × 0.85 ≈ 1,785 hm³
        capacity_mcm=1_785.0,
        capacity_m3=int(1_785.0 * 1_000_000),
        lat=46.8,
        lng=9.8,
        height=0,
        year_built=0,
        river_name_el="Inn/En",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="Tessin",
        name_el="Tessin (Ticino)",
        # ~1,200 GWh × 0.85 ≈ 1,020 hm³
        capacity_mcm=1_020.0,
        capacity_m3=int(1_020.0 * 1_000_000),
        lat=46.3,
        lng=8.8,
        height=0,
        year_built=0,
        river_name_el="Ticino/Tessin",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
    DamInfo(
        name_en="UebrigCH",
        name_el="Übriges Schweiz",
        # ~1,300 GWh × 0.85 ≈ 1,105 hm³
        capacity_mcm=1_105.0,
        capacity_m3=int(1_105.0 * 1_000_000),
        lat=47.0,
        lng=8.2,
        height=0,
        year_built=0,
        river_name_el="Aare/Reuss",
        type_el="Kraftmagasin",
        image_url="",
        wikipedia_url="",
    ),
]

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _SWITZERLAND_DAMS)

# Map name_en → DamInfo for fast lookup during CSV parsing
_NAME_TO_DAM: dict[str, DamInfo] = {d.name_en: d for d in _SWITZERLAND_DAMS}



def _parse_snapshot_from_row(
    row: dict[str, str], target_date: date
) -> PercentageSnapshot | None:
    """Parse a single CSV row into a PercentageSnapshot. Returns None on parse failure."""
    dam_percentages: list[DamPercentage] = []
    total_volume_mcm = 0.0

    for current_col, max_col, name_en in _REGION_COLUMNS:
        try:
            current_gwh = float(row[current_col])
            max_gwh = float(row[max_col])
        except (KeyError, ValueError) as exc:
            logger.warning("BFE CSV parse error for %s: %s", name_en, exc)
            return None

        if max_gwh <= 0:
            pct = 0.0
        else:
            pct = current_gwh / max_gwh
            pct = max(0.0, min(1.0, pct))

        dam_percentages.append(DamPercentage(dam_name_en=name_en, percentage=pct))
        dam = _NAME_TO_DAM.get(name_en)
        if dam:
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


def _parse_date_statistics_from_row(
    row: dict[str, str], target_date: date
) -> DateStatistics | None:
    """Parse a single CSV row into a DateStatistics. Returns None on parse failure."""
    dam_statistics: list[DamStatistic] = []

    for current_col, _max_col, name_en in _REGION_COLUMNS:
        try:
            current_gwh = float(row[current_col])
        except (KeyError, ValueError) as exc:
            logger.warning("BFE CSV parse error for %s stats: %s", name_en, exc)
            return None

        # Convert GWh → hm³ using Swiss hydro approximation
        storage_mcm = current_gwh * _GWH_TO_HM3
        dam_statistics.append(
            DamStatistic(
                dam_name_en=name_en,
                storage_mcm=storage_mcm,
                inflow_mcm=0.0,
            )
        )

    return DateStatistics(date=target_date, dam_statistics=dam_statistics)


class SwitzerlandProvider(BaseProvider):
    """DataProvider implementation for BFE Speicherseen OGD CSV weekly reservoir data.

    Fetches the full historical CSV from BFE and parses the last row for current
    state. The CSV covers weekly data from 2000 to present (~1,358 rows) and is
    published without authentication requirements. On any fetch or parse error,
    all regions default to 0.0 — the scheduler will retry at the next interval.
    """

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_SWITZERLAND_DAMS)

    async def _fetch_csv_text(self) -> str | None:
        """Fetch the BFE CSV. Returns None on any HTTP or network error."""
        try:
            response = await self._client.get(_CSV_PATH)
        except httpx.RequestError as exc:
            logger.warning("BFE CSV request failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning("BFE CSV returned HTTP %d", response.status_code)
            return None

        return response.text

    def _parse_all_rows(self, csv_text: str) -> list[dict[str, str]]:
        """Parse the CSV text and return all data rows as dicts."""
        reader = csv.DictReader(io.StringIO(csv_text))
        return list(reader)

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        csv_text = await self._fetch_csv_text()
        if csv_text is None:
            return zero_fill_snapshot(_SWITZERLAND_DAMS, _TOTAL_CAPACITY_MCM, target_date)

        rows = self._parse_all_rows(csv_text)
        if not rows:
            logger.warning("BFE CSV contained no data rows")
            return zero_fill_snapshot(_SWITZERLAND_DAMS, _TOTAL_CAPACITY_MCM, target_date)

        # Use the last row — CSV is sorted oldest-first, latest data is at the end
        last_row = rows[-1]
        snapshot = _parse_snapshot_from_row(last_row, target_date)
        if snapshot is None:
            return zero_fill_snapshot(_SWITZERLAND_DAMS, _TOTAL_CAPACITY_MCM, target_date)

        return snapshot

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        csv_text = await self._fetch_csv_text()
        if csv_text is None:
            return zero_fill_date_statistics(_SWITZERLAND_DAMS, target_date)

        rows = self._parse_all_rows(csv_text)
        if not rows:
            return zero_fill_date_statistics(_SWITZERLAND_DAMS, target_date)

        last_row = rows[-1]
        stats = _parse_date_statistics_from_row(last_row, target_date)
        if stats is None:
            return zero_fill_date_statistics(_SWITZERLAND_DAMS, target_date)

        return stats

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        """Parse ALL CSV rows to build the full historical timeseries (since 2000)."""
        csv_text = await self._fetch_csv_text()
        if csv_text is None:
            return []

        rows = self._parse_all_rows(csv_text)
        snapshots: list[PercentageSnapshot] = []

        for row in rows:
            datum_str = row.get("Datum", "").strip()
            if not datum_str:
                continue
            try:
                row_date = date.fromisoformat(datum_str)
            except ValueError as exc:
                logger.warning("BFE CSV invalid date '%s': %s", datum_str, exc)
                continue

            snapshot = _parse_snapshot_from_row(row, row_date)
            if snapshot is not None:
                snapshots.append(snapshot)

        return snapshots

