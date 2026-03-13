"""
Spain data provider — scrapes embalses.net for reservoir data.

Upstream: www.embalses.net (weekly updates, HTML scraping)
Covers Spain's 20 largest reservoirs by capacity, spanning 5 major
hydrographic basins: Guadiana, Tajo, Duero, Ebro, Guadalquivir.
"""
from __future__ import annotations

import logging
import re
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
# embalses.net has no metadata API; coordinates sourced from MITECO OGC API
# and verified against known dam locations.

_SPAIN_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="La Serena", name_el="La Serena",
        capacity_m3=3_219_000_000, capacity_mcm=3219.0,
        lat=38.863, lng=-5.440,
        height=60, year_built=1990,
        river_name_el="Zújar", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Alcantara", name_el="Alcántara",
        capacity_m3=3_160_000_000, capacity_mcm=3160.0,
        lat=39.718, lng=-6.893,
        height=130, year_built=1969,
        river_name_el="Tajo", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Almendra", name_el="Almendra",
        capacity_m3=2_649_000_000, capacity_mcm=2649.0,
        lat=41.220, lng=-6.360,
        height=202, year_built=1970,
        river_name_el="Tormes", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Buendia", name_el="Buendía",
        capacity_m3=1_705_000_000, capacity_mcm=1705.0,
        lat=40.375, lng=-2.791,
        height=78, year_built=1958,
        river_name_el="Guadiela", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Cijara", name_el="Cíjara",
        capacity_m3=1_505_000_000, capacity_mcm=1505.0,
        lat=39.341, lng=-5.005,
        height=70, year_built=1956,
        river_name_el="Guadiana", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Valdecanas", name_el="Valdecañas",
        capacity_m3=1_446_000_000, capacity_mcm=1446.0,
        lat=39.772, lng=-5.696,
        height=98, year_built=1964,
        river_name_el="Tajo", type_el="Arco-gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Mequinenza", name_el="Mequinenza",
        capacity_m3=1_373_000_000, capacity_mcm=1373.0,
        lat=41.370, lng=0.274,
        height=79, year_built=1966,
        river_name_el="Ebro", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ricobayo", name_el="Ricobayo",
        capacity_m3=1_145_000_000, capacity_mcm=1145.0,
        lat=41.520, lng=-5.990,
        height=99, year_built=1934,
        river_name_el="Esla", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Iznajar", name_el="Iznájar",
        capacity_m3=920_000_000, capacity_mcm=920.0,
        lat=37.276, lng=-4.387,
        height=120, year_built=1969,
        river_name_el="Genil", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Gabriel y Galan", name_el="Gabriel y Galán",
        capacity_m3=911_000_000, capacity_mcm=911.0,
        lat=40.222, lng=-6.133,
        height=60, year_built=1961,
        river_name_el="Alagón", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Alange", name_el="Alange",
        capacity_m3=852_000_000, capacity_mcm=852.0,
        lat=38.780, lng=-6.260,
        height=52, year_built=1992,
        river_name_el="Matachel", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="La Brena II", name_el="La Breña II",
        capacity_m3=823_000_000, capacity_mcm=823.0,
        lat=37.966, lng=-5.193,
        height=119, year_built=2009,
        river_name_el="Guadiato", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Entrepenas", name_el="Entrepeñas",
        capacity_m3=813_000_000, capacity_mcm=813.0,
        lat=40.572, lng=-2.706,
        height=83, year_built=1956,
        river_name_el="Tajo", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Orellana", name_el="Orellana",
        capacity_m3=808_000_000, capacity_mcm=808.0,
        lat=38.987, lng=-5.539,
        height=62, year_built=1963,
        river_name_el="Guadiana", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Canelles", name_el="Canelles",
        capacity_m3=679_000_000, capacity_mcm=679.0,
        lat=41.980, lng=0.611,
        height=150, year_built=1960,
        river_name_el="Noguera Ribagorzana", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Riano", name_el="Riaño",
        capacity_m3=641_000_000, capacity_mcm=641.0,
        lat=42.970, lng=-5.001,
        height=100, year_built=1987,
        river_name_el="Esla", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Andevalo", name_el="Andévalo",
        capacity_m3=634_000_000, capacity_mcm=634.0,
        lat=37.500, lng=-7.040,
        height=67, year_built=2004,
        river_name_el="Chanza", type_el="Materiales sueltos",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Negratin", name_el="Negratín",
        capacity_m3=571_000_000, capacity_mcm=571.0,
        lat=37.559, lng=-2.952,
        height=75, year_built=1984,
        river_name_el="Guadiana Menor", type_el="Bóveda",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Garcia de Sola", name_el="García de Sola",
        capacity_m3=554_000_000, capacity_mcm=554.0,
        lat=39.190, lng=-4.950,
        height=50, year_built=1963,
        river_name_el="Guadiana", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Embalse del Ebro", name_el="Embalse del Ebro",
        capacity_m3=541_000_000, capacity_mcm=541.0,
        lat=42.980, lng=-3.690,
        height=34, year_built=1952,
        river_name_el="Ebro", type_el="Gravedad",
        image_url="", wikipedia_url="",
    ),
]

# Map dam name_en → embalses.net URL path (pantano-{id}-{slug}.html)
_EMBALSES_URL_MAP: dict[str, str] = {
    "La Serena": "pantano-581-la-serena.html",
    "Alcantara": "pantano-1003-alcantara.html",
    "Almendra": "pantano-71-almendra.html",
    "Buendia": "pantano-931-buendia.html",
    "Cijara": "pantano-504-cijara.html",
    "Valdecanas": "pantano-1207-valdecanas.html",
    "Mequinenza": "pantano-298-mequinenza.html",
    "Ricobayo": "pantano-89-ricobayo.html",
    "Iznajar": "pantano-361-iznajar.html",
    "Gabriel y Galan": "pantano-977-gabriel-y-galan.html",
    "Alange": "pantano-471-alange.html",
    "La Brena II": "pantano-39-la-brena-ii.html",
    "Entrepenas": "pantano-967-entrepenas.html",
    "Orellana": "pantano-555-orellana.html",
    "Canelles": "pantano-1090-canelles.html",
    "Riano": "pantano-145-riano.html",
    "Andevalo": "pantano-476-andevalo.html",
    "Negratin": "pantano-397-negratin.html",
    "Garcia de Sola": "pantano-521-garcia-de-sola.html",
    "Embalse del Ebro": "pantano-221-ebro.html",
}

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _SPAIN_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _SPAIN_DAMS)

# ── Regex for scraping embalses.net HTML ──────────────────────────────────────
# HTML structure:
#   <div class="Campo"><strong>Agua embalsada (DD-MM-YYYY):</strong></div>
#   <div class="Resultado"><strong>2.933</strong></div>
#   <div class="Unidad"><strong>hm<sup ...>3</sup></strong></div>
#   <div class="Resultado"><strong>91,12</strong></div>
#   <div class="Unidad2"><strong>%</strong></div>
_VOLUME_RE = re.compile(
    r'Agua\s+embalsada\s*\([^)]*\).*?'
    r'class="Resultado"[^>]*><strong>([\d.,]+)</strong>.*?'
    r'class="Resultado"[^>]*><strong>([\d.,]+)</strong>',
    re.IGNORECASE | re.DOTALL,
)


def _parse_es_volume(raw: str) -> float:
    """Parse European-format volume string to float hm³.

    Dots are thousands separators for integer values: "2.792" → 2792.0
    Commas are decimal separators: "106,43" → 106.43
    """
    raw = raw.strip()
    if "," in raw:
        # European decimal: "106,43" → "106.43", "1.234,56" → "1234.56"
        raw = raw.replace(".", "").replace(",", ".")
    else:
        # Dots are thousands separators for whole numbers: "2.792" → "2792"
        raw = raw.replace(".", "")
    return float(raw)


def _parse_es_percentage(raw: str) -> float:
    """Parse percentage string: "88.35" or "88,35" → 88.35"""
    raw = raw.strip().replace(",", ".")
    return float(raw)


class SpainProvider:
    """DataProvider implementation for embalses.net (Spain reservoir data)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        # Per-sync cache: avoids re-scraping when fetch_date_statistics and
        # fetch_percentages are called back-to-back during the same sync cycle.
        self._page_cache: dict[str, tuple[float, float]] = {}

    def _clear_cache(self) -> None:
        self._page_cache.clear()

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_SPAIN_DAMS)

    async def _fetch_dam_page(self, dam_name: str) -> tuple[float, float]:
        """Fetch a single dam page and return (volume_mcm, percentage).

        Results are cached in _page_cache for the duration of the sync cycle.
        Returns (0.0, 0.0) on failure so individual dam errors don't
        break the entire sync.
        """
        if dam_name in self._page_cache:
            return self._page_cache[dam_name]

        url_path = _EMBALSES_URL_MAP.get(dam_name)
        if not url_path:
            logger.warning("No embalses.net URL for dam '%s'", dam_name)
            result = (0.0, 0.0)
            self._page_cache[dam_name] = result
            return result

        url = f"https://www.embalses.net/{url_path}"
        try:
            response = await self._client.get(url)
        except httpx.RequestError as exc:
            logger.warning("embalses.net request failed for %s: %s", dam_name, exc)
            result = (0.0, 0.0)
            self._page_cache[dam_name] = result
            return result

        if response.status_code != 200:
            logger.warning(
                "embalses.net returned HTTP %d for %s", response.status_code, dam_name
            )
            result = (0.0, 0.0)
            self._page_cache[dam_name] = result
            return result

        html = response.text
        match = _VOLUME_RE.search(html)
        if not match:
            logger.warning("Could not parse volume data from %s page", dam_name)
            result = (0.0, 0.0)
            self._page_cache[dam_name] = result
            return result

        volume_mcm = _parse_es_volume(match.group(1))
        percentage = _parse_es_percentage(match.group(2))
        result = (volume_mcm, percentage)
        self._page_cache[dam_name] = result
        return result

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0
        success_count = 0

        for dam in _SPAIN_DAMS:
            volume_mcm, pct_raw = await self._fetch_dam_page(dam.name_en)
            # Use parsed percentage (0-100) and convert to 0-1 fraction
            pct = pct_raw / 100.0 if pct_raw > 0 else 0.0
            dam_percentages.append(
                DamPercentage(dam_name_en=dam.name_en, percentage=pct)
            )
            total_volume_mcm += volume_mcm
            if pct_raw > 0:
                success_count += 1

        if success_count == 0:
            raise UpstreamAPIError(
                "embalses.net: failed to fetch data for any dam"
            )

        total_pct = (
            total_volume_mcm / _TOTAL_CAPACITY_MCM
            if _TOTAL_CAPACITY_MCM > 0
            else 0.0
        )

        # Clear cache after building the snapshot so next sync cycle
        # fetches fresh data. The cache only serves to avoid double-fetching
        # within the same sync call (fetch_date_statistics + fetch_percentages).
        self._clear_cache()

        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=total_pct,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        dam_statistics: list[DamStatistic] = []

        for dam in _SPAIN_DAMS:
            volume_mcm, _ = await self._fetch_dam_page(dam.name_en)
            dam_statistics.append(
                DamStatistic(
                    dam_name_en=dam.name_en,
                    storage_mcm=volume_mcm,
                    inflow_mcm=0.0,
                )
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        # embalses.net has no historical API; timeseries builds up
        # over time via the scheduler's incremental_sync calls.
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
