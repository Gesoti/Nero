"""
Czech Republic data provider — fetches from 5 Povodí (basin authority) portals.

Each of the 5 Czech basin authorities operates its own web portal that publishes
current reservoir fill levels. The portals fall into three HTML formats:

  1. "Objemy" pages (POH, PMO, PLA) — ASP.NET GridView rendered as a table with
     class "dataMereniGW". Each data row has an anchor with the reservoir name
     and a span whose id ends with "objemLbl" containing the fill percentage
     (comma decimal, e.g. "85,3" = 85.3%).

  2. PVL "Prehled" page — same dataMereniGW table, but the objemLbl span holds
     current volume in mil m³ (comma decimal). Percentage is computed:
         pct = (volume / capacity_mcm) * 100

  3. POD simple table — one <h3>/<table> pair per reservoir. The row whose label
     contains "Objem vody v" holds the volume (dot decimal, e.g. "180.530").
     Percentage computed the same way.

All parsers strip the "VD " prefix and use accent-folding for name matching so
that "VD Josefuv Dul" on the portal matches name_en "Josefuv Dul" and name_el
"Josefuv Dul" without requiring the caller to supply diacritics.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date

import httpx

from app.providers.base import (
    BaseProvider,
    DamInfo,
    DamPercentage,
    DamStatistic,
    DateStatistics,
    PercentageSnapshot,
)

logger = logging.getLogger(__name__)

# ── Hardcoded dam metadata ────────────────────────────────────────────────────
# Sourced from Czech water authority records.
# name_en: ASCII-safe for URL routing (diacritics removed).
# name_el: Czech name with diacritics (used to match portal text).

_CZECH_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Orlik", name_el="Orlik",
        capacity_m3=716_000_000, capacity_mcm=716.0,
        lat=49.5078, lng=14.1695,
        height=91, year_built=1963,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Lipno", name_el="Lipno",
        capacity_m3=306_000_000, capacity_mcm=306.0,
        lat=48.6333, lng=14.2167,
        height=25, year_built=1959,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nechranice", name_el="Nechranice",
        capacity_m3=288_000_000, capacity_mcm=288.0,
        lat=50.3722, lng=13.3917,
        height=48, year_built=1968,
        river_name_el="Ohre", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Slapy", name_el="Slapy",
        capacity_m3=270_000_000, capacity_mcm=270.0,
        lat=49.7833, lng=14.4167,
        height=67, year_built=1955,
        river_name_el="Vltava", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Svihov", name_el="Svihov",
        capacity_m3=267_000_000, capacity_mcm=267.0,
        lat=49.6667, lng=15.1500,
        height=58, year_built=1975,
        river_name_el="Zelivka", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Slezska Harta", name_el="Slezska Harta",
        capacity_m3=209_000_000, capacity_mcm=209.0,
        lat=49.9333, lng=17.1833,
        height=65, year_built=1997,
        river_name_el="Moravice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Nove Mlyny", name_el="Nove Mlyny",
        capacity_m3=142_000_000, capacity_mcm=142.0,
        lat=48.8500, lng=16.6500,
        height=18, year_built=1989,
        river_name_el="Dyje", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Vranov", name_el="Vranov",
        capacity_m3=133_000_000, capacity_mcm=133.0,
        lat=48.8917, lng=15.8167,
        height=47, year_built=1934,
        river_name_el="Dyje", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Dalesice", name_el="Dalesice",
        capacity_m3=127_000_000, capacity_mcm=127.0,
        lat=49.1333, lng=15.9167,
        height=100, year_built=1978,
        river_name_el="Jihlava", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Prisecnice", name_el="Prisecnice",
        capacity_m3=50_000_000, capacity_mcm=50.0,
        lat=50.4500, lng=13.0500,
        height=61, year_built=1976,
        river_name_el="Prisecnice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kruzberk", name_el="Kruzberk",
        capacity_m3=35_000_000, capacity_mcm=35.0,
        lat=49.8333, lng=17.5500,
        height=35, year_built=1955,
        river_name_el="Moravice", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Josefuv Dul", name_el="Josefuv Dul",
        capacity_m3=24_000_000, capacity_mcm=24.0,
        lat=50.7833, lng=15.1833,
        height=44, year_built=1982,
        river_name_el="Kamenice", type_el="Rockfill",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Flaje", name_el="Flaje",
        capacity_m3=23_000_000, capacity_mcm=23.0,
        lat=50.6833, lng=13.5833,
        height=59, year_built=1963,
        river_name_el="Flajsky potok", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Stanovice", name_el="Stanovice",
        capacity_m3=21_000_000, capacity_mcm=21.0,
        lat=50.2167, lng=12.8833,
        height=55, year_built=1978,
        river_name_el="Tepla", type_el="Gravity",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Zermanice", name_el="Zermanice",
        capacity_m3=25_000_000, capacity_mcm=25.0,
        lat=49.7333, lng=18.4833,
        height=32, year_built=1957,
        river_name_el="Lucina", type_el="Earthfill",
        image_url="", wikipedia_url="",
    ),
]

_CAPACITY_MAP: dict[str, float] = {d.name_en: d.capacity_mcm for d in _CZECH_DAMS}
_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _CZECH_DAMS)

# ── Portal configuration ───────────────────────────────────────────────────────
# Maps each portal URL to the list of dam name_en values it covers.

_PORTAL_URLS: dict[str, list[str]] = {
    "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": [
        "Nechranice", "Flaje", "Prisecnice", "Stanovice",
    ],
    "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": [
        "Dalesice", "Vranov", "Nove Mlyny",
    ],
    "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": [
        "Josefuv Dul",
    ],
    "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": [
        "Orlik", "Lipno", "Slapy", "Svihov",
    ],
    "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": [
        "Slezska Harta", "Kruzberk", "Zermanice",
    ],
}

_PARSER_TYPE: dict[str, str] = {
    "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": "objemy",
    "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": "objemy",
    "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": "objemy",
    "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": "pvl",
    "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": "pod",
}


# ── Number parsing helpers ────────────────────────────────────────────────────

def _parse_cz_number(text: str) -> float:
    """Parse a Czech-formatted number to float.

    Handles comma-decimal ("85,3" -> 85.3) and dot-decimal ("180.530" -> 180.53).
    POH/PMO/PLA/PVL use comma decimal; POD uses dot decimal.
    """
    stripped = text.strip()
    if "," in stripped:
        return float(stripped.replace(",", "."))
    return float(stripped)


def _strip_accents(text: str) -> str:
    """Remove diacritics for accent-insensitive comparison."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _normalize(text: str) -> str:
    """Lower-case and strip accents for robust name matching."""
    return _strip_accents(text).lower()


def _portal_name_matches_dam(portal_text: str, dam_name_en: str) -> bool:
    """Return True if a portal row label refers to the given dam.

    1. Strips "VD " prefix (present on all Czech portals).
    2. Accent-folds both sides.
    3. Substring matching handles long portal names like
       "VD Nove Mlyny - Dolni nadrz" matching dam "Nove Mlyny".
    """
    clean = portal_text.strip()
    if _normalize(clean).startswith("vd "):
        clean = clean[3:].strip()

    norm_portal = _normalize(clean)
    norm_en = _normalize(dam_name_en)

    return norm_en in norm_portal or norm_portal in norm_en


# ── Regex patterns (compiled once at module load) ─────────────────────────────

# Captures content of each <tr>...</tr> (DOTALL for multi-line rows)
_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)

# Captures text inside the first <a>...</a> in a row
_A_TEXT_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)

# Finds the span whose id ends with "objemLbl" and captures its numeric text
_OBJEM_SPAN_RE = re.compile(
    r'<span\b[^>]*id="[^"]*objemLbl"[^>]*>\s*([\d,. ]+?)\s*</span>',
    re.IGNORECASE | re.DOTALL,
)

# Strips all HTML tags to get plain text
_TAG_RE = re.compile(r"<[^>]+>")

# Matches <h3>...</h3> tags for POD section parsing
_H3_RE = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)


def _strip_tags(html: str) -> str:
    return _TAG_RE.sub("", html).strip()


# ── HTML parsers ──────────────────────────────────────────────────────────────

def _parse_objemy_page(html: str, dam_names: list[str]) -> dict[str, float]:
    """Parse a Povodí "Objemy" page (POH / PMO / PLA format).

    Scans <tr> blocks in the dataMereniGW table. For each data row:
    - Reads the anchor text as the portal reservoir name.
    - Reads the objemLbl span value as the fill percentage (comma decimal).

    Returns name_en -> percentage (0-100). Only dams in dam_names are included.
    """
    result: dict[str, float] = {}

    # Only process rows inside the dataMereniGW table
    table_match = re.search(
        r'<table\b[^>]*class="[^"]*dataMereniGW[^"]*"[^>]*>(.*?)</table>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not table_match:
        logger.warning("_parse_objemy_page: dataMereniGW table not found")
        return result

    table_html = table_match.group(1)

    for tr_match in _TR_RE.finditer(table_html):
        row_html = tr_match.group(1)

        a_match = _A_TEXT_RE.search(row_html)
        if not a_match:
            continue
        portal_name = _strip_tags(a_match.group(1))

        span_match = _OBJEM_SPAN_RE.search(row_html)
        if not span_match:
            continue

        try:
            pct = _parse_cz_number(span_match.group(1))
        except ValueError:
            logger.warning(
                "_parse_objemy_page: cannot parse '%s' as number", span_match.group(1)
            )
            continue

        for name in dam_names:
            if name not in result and _portal_name_matches_dam(portal_name, name):
                result[name] = pct
                break

    return result


def _parse_pvl_page(html: str, capacity_map: dict[str, float]) -> dict[str, float]:
    """Parse the PVL "Prehled" page (www.pvl.cz).

    Same dataMereniGW table structure as Objemy pages, but the objemLbl span
    contains the current volume in mil m3, not a percentage. We compute:
        percentage = (volume / capacity_mcm) * 100

    Returns name_en -> percentage (0-100). Only dams in capacity_map are included.
    """
    result: dict[str, float] = {}

    table_match = re.search(
        r'<table\b[^>]*class="[^"]*dataMereniGW[^"]*"[^>]*>(.*?)</table>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not table_match:
        logger.warning("_parse_pvl_page: dataMereniGW table not found")
        return result

    table_html = table_match.group(1)

    for tr_match in _TR_RE.finditer(table_html):
        row_html = tr_match.group(1)

        a_match = _A_TEXT_RE.search(row_html)
        if not a_match:
            continue
        portal_name = _strip_tags(a_match.group(1))

        span_match = _OBJEM_SPAN_RE.search(row_html)
        if not span_match:
            continue

        try:
            volume = _parse_cz_number(span_match.group(1))
        except ValueError:
            logger.warning(
                "_parse_pvl_page: cannot parse volume '%s'", span_match.group(1)
            )
            continue

        for name, capacity in capacity_map.items():
            if name not in result and _portal_name_matches_dam(portal_name, name):
                if capacity > 0:
                    result[name] = (volume / capacity) * 100.0
                break

    return result


def _parse_pod_page(html: str, capacity_map: dict[str, float]) -> dict[str, float]:
    """Parse the POD simple HTML page (www.pod.cz).

    Sections are delimited by <h3>RESERVOIR NAME</h3>. Each section has a
    plain <table> where the row whose label contains "Objem vody v" holds
    the current volume in mil m3 (dot decimal). Percentage computed from capacity.

    Each <tr> is split into individual <td> cells so that the volume value in
    the second cell is read directly, without interference from the "(mil.m3)"
    text in the label cell.

    Returns name_en -> percentage (0-100). Only dams in capacity_map are included.
    """
    result: dict[str, float] = {}

    # Match individual <td> cells within a row
    _td_re = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)

    h3_positions = [
        (m.start(), m.end(), _strip_tags(m.group(1)))
        for m in _H3_RE.finditer(html)
    ]

    for idx, (_, h3_end, header_text) in enumerate(h3_positions):
        section_end = h3_positions[idx + 1][0] if idx + 1 < len(h3_positions) else len(html)
        section_html = html[h3_end:section_end]

        volume: float | None = None
        for tr_match in _TR_RE.finditer(section_html):
            row_html = tr_match.group(1)
            cells = [_strip_tags(m.group(1)) for m in _td_re.finditer(row_html)]
            if len(cells) >= 2 and "Objem vody v" in cells[0]:
                # Second cell holds the volume value; label cell may contain "(mil.m3)"
                try:
                    volume = _parse_cz_number(cells[1])
                except ValueError:
                    logger.warning(
                        "_parse_pod_page: cannot parse volume '%s' for '%s'",
                        cells[1], header_text,
                    )
                break

        if volume is None:
            continue

        for name, capacity in capacity_map.items():
            if name not in result and _portal_name_matches_dam(header_text, name):
                if capacity > 0:
                    result[name] = (volume / capacity) * 100.0
                break

    return result


# ── Provider class ─────────────────────────────────────────────────────────────

class CzechProvider(BaseProvider):
    """DataProvider for Czech Republic reservoir data.

    Fetches live fill-level data from 5 Povodí (basin authority) portals.
    If any portal is unreachable or returns unparseable HTML, those dams fall
    back to 0.0 — the remaining portals are unaffected.
    """

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_CZECH_DAMS)

    async def _fetch_portal(self, url: str) -> str | None:
        """Fetch a single portal page.  Returns HTML text or None on failure.

        PVL has known SSL certificate issues so verification is skipped for it.
        """
        try:
            kwargs: dict[str, object] = {}
            if "pvl.cz" in url:
                kwargs["verify"] = False
            response = await self._client.get(url, **kwargs)
        except httpx.RequestError as exc:
            logger.warning("Czech portal request failed [%s]: %s", url, exc)
            return None

        if response.status_code != 200:
            logger.warning(
                "Czech portal returned HTTP %d [%s]", response.status_code, url
            )
            return None

        return response.text

    async def _collect_percentages(self) -> dict[str, float]:
        """Fetch all 5 portals and return a merged name_en -> percentage map.

        Sequential fetching avoids overwhelming small government servers.
        Per-portal failures are logged but do not abort the overall collection.
        """
        pct_map: dict[str, float] = {}

        for url, dam_names in _PORTAL_URLS.items():
            html = await self._fetch_portal(url)
            if html is None:
                logger.warning(
                    "Skipping %d dams from %s (portal unreachable)", len(dam_names), url
                )
                continue

            parser_type = _PARSER_TYPE[url]

            if parser_type == "objemy":
                parsed = _parse_objemy_page(html, dam_names)
            elif parser_type == "pvl":
                cap_map = {n: _CAPACITY_MAP[n] for n in dam_names if n in _CAPACITY_MAP}
                parsed = _parse_pvl_page(html, cap_map)
            else:  # pod
                cap_map = {n: _CAPACITY_MAP[n] for n in dam_names if n in _CAPACITY_MAP}
                parsed = _parse_pod_page(html, cap_map)

            pct_map.update(parsed)
            logger.debug(
                "Czech portal %s: parsed %d/%d dams", url, len(parsed), len(dam_names)
            )

        return pct_map

    def _build_snapshot(
        self, pct_map: dict[str, float], target_date: date
    ) -> PercentageSnapshot:
        """Build a PercentageSnapshot from a name_en -> percentage map.

        Missing dams default to 0.0. total_percentage is capacity-weighted.
        """
        dam_percentages: list[DamPercentage] = []
        weighted_sum: float = 0.0

        for dam in _CZECH_DAMS:
            pct = pct_map.get(dam.name_en, 0.0)
            dam_percentages.append(DamPercentage(dam_name_en=dam.name_en, percentage=pct))
            weighted_sum += pct * dam.capacity_mcm

        total_pct = weighted_sum / _TOTAL_CAPACITY_MCM if _TOTAL_CAPACITY_MCM > 0 else 0.0

        return PercentageSnapshot(
            date=target_date,
            dam_percentages=dam_percentages,
            total_percentage=total_pct,
            total_capacity_mcm=_TOTAL_CAPACITY_MCM,
        )

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        pct_map = await self._collect_percentages()
        return self._build_snapshot(pct_map, target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        # Czech portals expose fill levels but not inflow; derive storage_mcm from pct.
        pct_map = await self._collect_percentages()

        dam_statistics: list[DamStatistic] = [
            DamStatistic(
                dam_name_en=dam.name_en,
                storage_mcm=(pct_map.get(dam.name_en, 0.0) / 100.0) * dam.capacity_mcm,
                inflow_mcm=0.0,
            )
            for dam in _CZECH_DAMS
        ]
        return DateStatistics(date=target_date, dam_statistics=dam_statistics)

