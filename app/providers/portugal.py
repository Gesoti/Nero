"""
Portugal data provider — fetches from infoagua.apambiente.pt embedded JSON.

Upstream: infoagua.apambiente.pt (monthly updates, embedded JS data)
Covers Portugal's 20 largest reservoirs by capacity, spanning major
hydrographic basins: Guadiana, Tejo, Douro, Cávado, Mondego, and others.
"""
from __future__ import annotations

import json
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
# Sourced from infoagua.apambiente.pt DATA_SupStations. Capacity and
# coordinates verified against SNIRH records.

_PORTUGAL_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Alqueva", name_el="Alqueva",
        capacity_m3=4_150_000_000, capacity_mcm=4150.0,
        lat=38.197, lng=-7.495,
        height=96, year_built=2002,
        river_name_el="Guadiana", type_el="Gravidade/Enrocamento",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Baixo Sabor", name_el="Baixo Sabor",
        capacity_m3=1_095_000_000, capacity_mcm=1095.0,
        lat=41.229, lng=-7.013,
        height=123, year_built=2014,
        river_name_el="Sabor", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Castelo de Bode", name_el="Castelo de Bode",
        capacity_m3=1_095_000_000, capacity_mcm=1095.0,
        lat=39.545, lng=-8.323,
        height=115, year_built=1951,
        river_name_el="Zêzere", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Cabril", name_el="Cabril",
        capacity_m3=720_000_000, capacity_mcm=720.0,
        lat=39.929, lng=-8.127,
        height=132, year_built=1954,
        river_name_el="Zêzere", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Alto Rabagao", name_el="Alto Rabagão",
        capacity_m3=568_700_000, capacity_mcm=568.7,
        lat=41.732, lng=-7.861,
        height=94, year_built=1964,
        river_name_el="Rabagão", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Santa Clara", name_el="Santa Clara",
        capacity_m3=485_000_000, capacity_mcm=485.0,
        lat=37.516, lng=-8.440,
        height=82, year_built=1969,
        river_name_el="Mira", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Aguieira", name_el="Aguieira",
        capacity_m3=423_000_000, capacity_mcm=423.0,
        lat=40.341, lng=-8.197,
        height=89, year_built=1981,
        river_name_el="Mondego", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Alto Lindoso", name_el="Alto Lindoso",
        capacity_m3=379_000_000, capacity_mcm=379.0,
        lat=41.871, lng=-8.205,
        height=110, year_built=1992,
        river_name_el="Lima", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Maranhao", name_el="Maranhão",
        capacity_m3=205_400_000, capacity_mcm=205.4,
        lat=39.015, lng=-7.976,
        height=55, year_built=1957,
        river_name_el="Sever", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Caia", name_el="Caia",
        capacity_m3=203_000_000, capacity_mcm=203.0,
        lat=38.996, lng=-7.140,
        height=52, year_built=1967,
        river_name_el="Caia", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Paradela", name_el="Paradela",
        capacity_m3=164_400_000, capacity_mcm=164.4,
        lat=41.761, lng=-7.957,
        height=112, year_built=1958,
        river_name_el="Cávado", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Montargil", name_el="Montargil",
        capacity_m3=164_300_000, capacity_mcm=164.3,
        lat=39.053, lng=-8.175,
        height=33, year_built=1958,
        river_name_el="Sor", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Canicada", name_el="Caniçada",
        capacity_m3=159_300_000, capacity_mcm=159.3,
        lat=41.652, lng=-8.235,
        height=76, year_built=1955,
        river_name_el="Cávado", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Odelouca", name_el="Odelouca",
        capacity_m3=157_000_000, capacity_mcm=157.0,
        lat=37.287, lng=-8.471,
        height=65, year_built=2012,
        river_name_el="Odelouca", type_el="Enrocamento",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Carrapatelo", name_el="Carrapatelo",
        capacity_m3=150_200_000, capacity_mcm=150.2,
        lat=41.088, lng=-8.126,
        height=57, year_built=1972,
        river_name_el="Douro", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ribeiradio", name_el="Ribeiradio",
        capacity_m3=136_400_000, capacity_mcm=136.4,
        lat=40.742, lng=-8.319,
        height=75, year_built=2015,
        river_name_el="Vouga", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Alvito", name_el="Alvito",
        capacity_m3=132_500_000, capacity_mcm=132.5,
        lat=38.275, lng=-7.921,
        height=48, year_built=1976,
        river_name_el="Odivelas", type_el="Terra",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Odeleite", name_el="Odeleite",
        capacity_m3=130_000_000, capacity_mcm=130.0,
        lat=37.331, lng=-7.518,
        height=64, year_built=1997,
        river_name_el="Odeleite", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Bemposta", name_el="Bemposta",
        capacity_m3=128_800_000, capacity_mcm=128.8,
        lat=41.298, lng=-6.471,
        height=87, year_built=1964,
        river_name_el="Douro", type_el="Abóbada",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Torrao", name_el="Torrão",
        capacity_m3=123_900_000, capacity_mcm=123.9,
        lat=41.098, lng=-8.262,
        height=60, year_built=1988,
        river_name_el="Tâmega", type_el="Gravidade",
        image_url="", wikipedia_url="",
    ),
]

# Map name_en → upstream DATA_SupStations "name" field (uppercase)
_UPSTREAM_NAME_MAP: dict[str, str] = {
    "Alqueva": "ALQUEVA",
    "Baixo Sabor": "BAIXO SABOR",
    "Castelo de Bode": "CASTELO DE BODE",
    "Cabril": "CABRIL",
    "Alto Rabagao": "ALTO RABAGÃO",
    "Santa Clara": "ST.A CLARA",
    "Aguieira": "AGUIEIRA",
    "Alto Lindoso": "ALTO LINDOSO",
    "Maranhao": "MARANHÃO",
    "Caia": "CAIA",
    "Paradela": "PARADELA",
    "Montargil": "MONTARGIL",
    "Canicada": "CANIÇADA",
    "Odelouca": "ODELOUCA",
    "Carrapatelo": "CARRAPATELO",
    "Ribeiradio": "RIBEIRADIO",
    "Alvito": "ALVITO",
    "Odeleite": "ODELEITE",
    "Bemposta": "BEMPOSTA",
    "Torrao": "TORRÃO",
}

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _PORTUGAL_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _PORTUGAL_DAMS)

# Regex to extract DATA_SupStations JSON array from HTML
_DATA_RE = re.compile(
    r'var\s+DATA_SupStations\s*=\s*(\[.*?\])\s*;',
    re.DOTALL,
)

_INFOAGUA_URL = "/pt/seca/secas-pesquisa"


def _parse_pt_volume(raw: str) -> float:
    """Parse volume string from infoagua (e.g., '4054.512') to float hm³.

    The source uses dot as decimal separator (not European format).
    """
    return float(raw.strip())


class PortugalProvider:
    """DataProvider implementation for infoagua.apambiente.pt (Portugal reservoir data)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._cached_data: dict[str, dict[str, str | float]] | None = None

    def _clear_cache(self) -> None:
        self._cached_data = None

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_PORTUGAL_DAMS)

    async def _fetch_upstream_data(self) -> dict[str, dict[str, str | float]]:
        """Fetch infoagua page, extract DATA_SupStations, return dict keyed by name."""
        if self._cached_data is not None:
            return self._cached_data

        try:
            response = await self._client.get(_INFOAGUA_URL)
        except httpx.RequestError as exc:
            raise UpstreamAPIError(f"infoagua request failed: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamAPIError(
                f"infoagua returned HTTP {response.status_code}"
            )

        html = response.text
        match = _DATA_RE.search(html)
        if not match:
            raise UpstreamAPIError("Could not find DATA_SupStations in infoagua page")

        try:
            stations: list[dict[str, str | float]] = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise UpstreamAPIError(f"Failed to parse DATA_SupStations JSON: {exc}") from exc

        # Build lookup by name
        result: dict[str, dict[str, str | float]] = {}
        for station in stations:
            name = str(station.get("name", ""))
            result[name] = station

        self._cached_data = result
        return result

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        upstream = await self._fetch_upstream_data()

        dam_percentages: list[DamPercentage] = []
        total_volume_mcm = 0.0

        for dam in _PORTUGAL_DAMS:
            upstream_name = _UPSTREAM_NAME_MAP.get(dam.name_en, "")
            station = upstream.get(upstream_name)

            if station and station.get("recent_value_percentage"):
                pct_raw = float(station["recent_value_percentage"])
                pct = pct_raw / 100.0
                raw_vol = str(station.get("recent_value", "0"))
                volume_mcm = _parse_pt_volume(raw_vol)
            else:
                pct = 0.0
                volume_mcm = 0.0

            dam_percentages.append(
                DamPercentage(dam_name_en=dam.name_en, percentage=pct)
            )
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
        upstream = await self._fetch_upstream_data()

        dam_statistics: list[DamStatistic] = []

        for dam in _PORTUGAL_DAMS:
            upstream_name = _UPSTREAM_NAME_MAP.get(dam.name_en, "")
            station = upstream.get(upstream_name)

            if station and station.get("recent_value"):
                raw_vol = str(station["recent_value"])
                storage_mcm = _parse_pt_volume(raw_vol)
            else:
                storage_mcm = 0.0

            dam_statistics.append(
                DamStatistic(
                    dam_name_en=dam.name_en,
                    storage_mcm=storage_mcm,
                    inflow_mcm=0.0,
                )
            )

        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        # infoagua has no historical API; timeseries builds up
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
