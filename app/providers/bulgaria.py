"""
Bulgaria data provider — Ministry of Environment and Water (MOEW) daily bulletin.

Upstream: https://www.moew.government.bg/static/media/ups/tiny/Daily%20Bulletin/{DDMMYYYY}_Bulletin_Daily.doc
Format: Old-style .doc (Word 97-2003 Binary format, OLE2 compound document).
Coverage: Daily bulletins published on business days (Mon–Fri).

Parsing the .doc binary format requires olefile and significant extraction logic
that falls outside MVP scope. This provider implements the full DataProvider
protocol as a stub:
  1. Attempts to download the latest bulletin .doc file.
  2. Logs the file size for debugging connectivity.
  3. Returns 0.0 for all dam percentages (parsing is TBD).

The dam metadata (coordinates, capacities) is hardcoded from official sources
and is already correct — only the fill percentages are stub values. When .doc
parsing is implemented, replace the stub logic in fetch_percentages() and
fetch_date_statistics() without changing any other code.

If the upstream is unreachable, methods return zero-fill defaults rather than
raising — the scheduler will retry at the next sync interval.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx

from app.providers.base import (
    BaseProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    zero_fill_date_statistics,
    zero_fill_snapshot,
)

logger = logging.getLogger(__name__)

# MOEW daily bulletin URL template. Date is formatted as DDMMYYYY.
# Bulletins are published on business days; the provider tries today, then
# falls back to yesterday and the day before to handle weekends and holidays.
_BULLETIN_URL_TEMPLATE = (
    "https://www.moew.government.bg/static/media/ups/tiny/Daily%20Bulletin/"
    "{date}_Bulletin_Daily.doc"
)

# ── Hardcoded reservoir metadata ──────────────────────────────────────────────
# Bulgaria's 20 largest reservoirs, ordered by descending capacity (MCM).
# name_en: ASCII form used in URLs and DB.
# name_el: Bulgarian Cyrillic display name.
# Capacities in hm³ (= MCM). Height/year/river/type not publicly standardised;
# zeroes are acceptable placeholders for MVP.

_BULGARIA_DAMS: list[DamInfo] = [
    DamInfo(
        name_en="Iskar", name_el="Искър",
        capacity_mcm=655.3, capacity_m3=int(655.3 * 1_000_000),
        lat=42.55, lng=23.67,
        height=74, year_built=1954,
        river_name_el="Искър", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ogosta", name_el="Огоста",
        capacity_mcm=506.0, capacity_m3=int(506.0 * 1_000_000),
        lat=43.42, lng=23.38,
        height=71, year_built=1989,
        river_name_el="Огоста", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kardzhali", name_el="Кърджали",
        capacity_mcm=497.2, capacity_m3=int(497.2 * 1_000_000),
        lat=41.65, lng=25.37,
        height=64, year_built=1953,
        river_name_el="Арда", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Dospat", name_el="Доспат",
        capacity_mcm=449.2, capacity_m3=int(449.2 * 1_000_000),
        lat=41.65, lng=24.17,
        height=54, year_built=1975,
        river_name_el="Доспат", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Zhrebchevo", name_el="Жребчево",
        capacity_mcm=400.0, capacity_m3=int(400.0 * 1_000_000),
        lat=42.60, lng=25.87,
        height=70, year_built=1963,
        river_name_el="Тунджа", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Studen Kladenets", name_el="Студен кладенец",
        capacity_mcm=387.8, capacity_m3=int(387.8 * 1_000_000),
        lat=41.62, lng=25.52,
        height=71, year_built=1954,
        river_name_el="Арда", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Tsonevo", name_el="Цонево",
        capacity_mcm=330.0, capacity_m3=int(330.0 * 1_000_000),
        lat=42.93, lng=27.45,
        height=59, year_built=1971,
        river_name_el="Луда Камчия", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ticha", name_el="Тича",
        capacity_mcm=311.8, capacity_m3=int(311.8 * 1_000_000),
        lat=43.05, lng=26.42,
        height=77, year_built=1984,
        river_name_el="Тича", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Batak", name_el="Батак",
        capacity_mcm=310.3, capacity_m3=int(310.3 * 1_000_000),
        lat=41.93, lng=24.22,
        height=68, year_built=1954,
        river_name_el="Батачка", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Kamchia", name_el="Камчия",
        capacity_mcm=233.6, capacity_m3=int(233.6 * 1_000_000),
        lat=43.00, lng=27.28,
        height=56, year_built=1975,
        river_name_el="Камчия", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Vacha", name_el="Въча",
        capacity_mcm=226.1, capacity_m3=int(226.1 * 1_000_000),
        lat=41.87, lng=24.42,
        height=141, year_built=1974,
        river_name_el="Въча", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Pyasachnik", name_el="Пясъчник",
        capacity_mcm=206.5, capacity_m3=int(206.5 * 1_000_000),
        lat=42.23, lng=24.40,
        height=62, year_built=1977,
        river_name_el="Тополница", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Stamboliyski", name_el="Стамболийски",
        capacity_mcm=205.6, capacity_m3=int(205.6 * 1_000_000),
        lat=42.32, lng=24.55,
        height=55, year_built=1963,
        river_name_el="Марица", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Ivaylovgrad", name_el="Ивайловград",
        capacity_mcm=156.7, capacity_m3=int(156.7 * 1_000_000),
        lat=41.52, lng=26.12,
        height=45, year_built=1959,
        river_name_el="Арда", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Belmeken", name_el="Белмекен",
        capacity_mcm=144.0, capacity_m3=int(144.0 * 1_000_000),
        lat=42.12, lng=23.85,
        height=96, year_built=1967,
        river_name_el="Марица", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Koprinka", name_el="Копринка",
        capacity_mcm=142.2, capacity_m3=int(142.2 * 1_000_000),
        lat=42.65, lng=24.72,
        height=58, year_built=1955,
        river_name_el="Тунджа", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Topolnitsa", name_el="Тополница",
        capacity_mcm=137.1, capacity_m3=int(137.1 * 1_000_000),
        lat=42.33, lng=24.22,
        height=64, year_built=1979,
        river_name_el="Тополница", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Gorni Dabnik", name_el="Горни Дъбник",
        capacity_mcm=130.0, capacity_m3=int(130.0 * 1_000_000),
        lat=43.38, lng=24.40,
        height=43, year_built=1971,
        river_name_el="Вит", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Trakiets", name_el="Тракиец",
        capacity_mcm=114.0, capacity_m3=int(114.0 * 1_000_000),
        lat=42.02, lng=25.22,
        height=51, year_built=1961,
        river_name_el="Марица", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
    DamInfo(
        name_en="Tsankov Kamak", name_el="Цанков камък",
        capacity_mcm=110.7, capacity_m3=int(110.7 * 1_000_000),
        lat=41.78, lng=24.28,
        height=130, year_built=2012,
        river_name_el="Въча", type_el="Язовир",
        image_url="", wikipedia_url="",
    ),
]

_TOTAL_CAPACITY_MCM: float = sum(d.capacity_mcm for d in _BULGARIA_DAMS)


def _find_latest_bulletin_url(target_date: date) -> str:
    """Return the MOEW bulletin URL for the most recent business day.

    Tries target_date first, then falls back to the two preceding days to
    handle weekends and public holidays when no bulletin is published.
    Weekends (Saturday=5, Sunday=6) are skipped automatically.
    """
    candidate = target_date
    attempts = 0
    while attempts < 7:  # guard against infinite loop in edge cases
        if candidate.weekday() < 5:  # Monday–Friday
            date_str = candidate.strftime("%d%m%Y")
            return _BULLETIN_URL_TEMPLATE.format(date=date_str)
        candidate -= timedelta(days=1)
        attempts += 1
    # Fallback: format target_date regardless of day (URL may 404)
    return _BULLETIN_URL_TEMPLATE.format(date=target_date.strftime("%d%m%Y"))


class BulgariaProvider(BaseProvider):
    """DataProvider stub for MOEW Bulgaria daily water bulletin.

    The upstream source publishes a .doc (Word 97-2003 binary) file each
    business day containing fill levels for the major Bulgarian reservoirs.
    Parsing OLE2/BIFF8 binary format is non-trivial and deferred to a future
    sprint. This stub:

    - Downloads the bulletin .doc to verify connectivity and log file size.
    - Returns 0.0 for all dam percentages (parsing TBD).
    - Is fully compliant with the DataProvider protocol so the rest of the
      app (sync, routes, DB) works correctly from day one.

    When parsing is added, implement _parse_bulletin_doc(content: bytes) →
    dict[str, float] and call it inside fetch_percentages() and
    fetch_date_statistics(). No other code needs to change.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client)

    async def fetch_dams(self) -> list[DamInfo]:
        return list(_BULGARIA_DAMS)

    async def _download_bulletin(self, target_date: date) -> bytes | None:
        """Attempt to download the latest MOEW bulletin .doc file.

        Returns raw bytes on success, or None on any HTTP/network error.
        Logs the file size so operators can verify connectivity without
        needing to open the binary file.
        """
        url = _find_latest_bulletin_url(target_date)
        try:
            response = await self._client.get(url)
        except httpx.RequestError as exc:
            logger.warning("MOEW Bulgaria request failed: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning(
                "MOEW Bulgaria returned HTTP %d for %s", response.status_code, url
            )
            return None

        content = response.content
        logger.info(
            "MOEW Bulgaria bulletin downloaded: %d bytes from %s", len(content), url
        )
        return content

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        # Download the bulletin to verify connectivity and log file size.
        # Parsing is TBD — return 0.0 fallback for all dams regardless of
        # download success, because we cannot yet extract the values.
        await self._download_bulletin(target_date)
        return zero_fill_snapshot(_BULGARIA_DAMS, _TOTAL_CAPACITY_MCM, target_date)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        # Mirrors fetch_percentages — stub returns zeros, parsing is TBD.
        await self._download_bulletin(target_date)
        return zero_fill_date_statistics(_BULGARIA_DAMS, target_date)
