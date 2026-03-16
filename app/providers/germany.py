"""
Germany data provider.

Upstream sources:
  - Talsperrenleitzentrale Ruhr: https://www.talsperrenleitzentrale-ruhr.de/online-daten/talsperren
    9 dams in the Ruhr catchment. Live HTML updated ~15-min to hourly.
    Parsed via BeautifulSoup: `<div id="dam-coordinates">` contains one `<div
    title="<DamName>" id="dam-popover-<id>">` per dam; volume is in the text
    node as "Stauinhalt: 162.01 Mio.m³".
  - Sachsen LTV: https://www.ltv.sachsen.de — deferred (parser not yet implemented).
  - Others: Thuringia (TLUG), Harz (Harzwasserwerke), Wupperverband — deferred.
"""
from __future__ import annotations

import logging
import re
from datetime import date

import httpx
from bs4 import BeautifulSoup

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

# Path on the Ruhr portal that contains all 9 dam cards in a single HTML page.
_RUHR_URL = "/online-daten/talsperren"

# Maps portal `title` attribute values → our name_en keys.
# Only covers Ruhr dams that are present in _GERMANY_DAMS.
# Ennepe, Furwigge, Henne, Lister, Ahausen are Ruhr dams not in our top-15 list.
_RUHR_NAME_MAP: dict[str, str] = {
    "Biggetalsperre": "Bigge",
    "Möhnetalsperre": "Mohne",
    "Sorpetalsperre": "Sorpe",
    "Versetalsperre": "Verse",
}

# Build a lookup of name_en → capacity_mcm for fast percentage computation.
_CAPACITY_BY_NAME: dict[str, float] = {d.name_en: d.capacity_mcm for d in _GERMANY_DAMS}

# Matches the Stauinhalt line, e.g. "Stauinhalt: 162.01 Mio.m³"
# Volume uses dot as decimal separator (standard, not German comma).
_VOLUME_RE = re.compile(r"Stauinhalt\s*:\s*([\d.]+)\s*Mio", re.IGNORECASE)


def _parse_ruhr_page(html: str) -> dict[str, float]:
    """Parse the Ruhr portal HTML and return {name_en: fill_percentage (0-1)}.

    Structure: <div id="dam-coordinates"> contains one <div title="DamName"
    id="dam-popover-*"> per dam. The dam's current storage volume appears in
    the text node as "Stauinhalt: 162.01 Mio.m³". Percentage is computed as
    volume / capacity_mcm, clamped to [0, 1].

    Unknown dam names (not in _RUHR_NAME_MAP) are silently skipped.
    Cards without a parseable volume are logged as warnings and skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(id="dam-coordinates")
    if container is None:
        return {}

    result: dict[str, float] = {}
    for card in container.find_all("div", id=re.compile(r"^dam-popover-")):
        portal_name: str = card.get("title", "").strip()
        name_en = _RUHR_NAME_MAP.get(portal_name)
        if name_en is None:
            # Ruhr dam not in our top-15 list — expected for Ennepe etc.
            continue

        card_text = card.get_text(separator=" ")
        match = _VOLUME_RE.search(card_text)
        if match is None:
            logger.warning(
                "Ruhr portal: no Stauinhalt found in card for %s", portal_name
            )
            continue

        try:
            volume_mcm = float(match.group(1))
        except ValueError:
            logger.warning(
                "Ruhr portal: could not parse volume '%s' for %s",
                match.group(1), portal_name,
            )
            continue

        capacity = _CAPACITY_BY_NAME[name_en]
        percentage = min(volume_mcm / capacity, 1.0)
        result[name_en] = percentage

    return result


def _build_snapshot(target_date: date, parsed: dict[str, float]) -> PercentageSnapshot:
    """Merge parsed Ruhr percentages with zero-fill defaults for non-Ruhr dams."""
    dam_percentages = [
        DamPercentage(
            dam_name_en=d.name_en,
            percentage=parsed.get(d.name_en, 0.0),
        )
        for d in _GERMANY_DAMS
    ]
    total_volume = sum(
        parsed.get(d.name_en, 0.0) * d.capacity_mcm for d in _GERMANY_DAMS
    )
    total_percentage = total_volume / _TOTAL_CAPACITY_MCM if _TOTAL_CAPACITY_MCM else 0.0
    return PercentageSnapshot(
        date=target_date,
        dam_percentages=dam_percentages,
        total_percentage=total_percentage,
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
    """DataProvider for German reservoir data.

    Live fill percentages are fetched from the Talsperrenleitzentrale Ruhr
    portal (Bigge, Mohne, Sorpe, Verse). Non-Ruhr dams remain 0.0 until their
    parsers are added. All errors fall back gracefully to zero-fill so the
    scheduler always produces a valid snapshot.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_GERMANY_DAMS)

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        """Fetch and parse the Ruhr portal page; return percentages for all 15 dams.

        Ruhr dams covered: Bigge, Mohne, Sorpe, Verse.
        Non-Ruhr dams (Saxony, Harz etc.) remain 0.0 until their parsers are added.
        Any network or parse error causes a graceful fallback to all-zeros.
        """
        try:
            response = await self._client.get(_RUHR_URL)
            response.raise_for_status()
            parsed = _parse_ruhr_page(response.text)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("Talsperrenleitzentrale Ruhr fetch failed: %s", exc)
            parsed = {}
        except Exception as exc:  # noqa: BLE001 — broad catch is intentional; parse errors must not crash sync
            logger.error("Unexpected error parsing Ruhr page: %s", exc)
            parsed = {}

        return _build_snapshot(target_date, parsed)

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
