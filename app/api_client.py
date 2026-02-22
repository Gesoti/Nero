"""
HTTP client for the Cyprus Water Development Department upstream API.
Shared httpx.AsyncClient is reused across requests; call close_client() on shutdown.

Actual API response shapes (verified against live API 2026-02-19):

/dams → list of {nameEn, nameEl, yearOfConstruction, height, capacity (m3),
                  lat, lng, riverNameEl, typeEl, imageUrl, wikipediaUrl}

/timeseries → {dams: [...], percentages: {"YYYY-MM-DD": {damNamesToPercentage,
               date, totalPercentage, totalCapacityInMCM}}, numOfDams, numOfPercentageEntries}

/percentages?date=YYYY-MM-DD → {damNamesToPercentage: {name: pct},
                                  date: "Feb 18...", totalPercentage, totalCapacityInMCM}

/date-statistics?date=YYYY-MM-DD → {timestamp, date, storageInMCM: {name: val},
                                      inflowInMCM: {name: val}}

/monthly-inflows → list of {timestamp, year, period, periodOrder, inflowInMCM}

/events?from=YYYY-MM-DD&to=YYYY-MM-DD → list of {nameEn, nameEl, type,
                                                    description, from (ms), until (ms)}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Shared client (created lazily, closed on app shutdown) ────────────────────
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.upstream_base_url,
            headers={"User-Agent": "CyprusWaterDashboard/1.0"},
            timeout=httpx.Timeout(
                connect=5.0,
                read=settings.upstream_timeout_seconds,
                write=5.0,
                pool=5.0,
            ),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()


# ── Domain dataclasses ────────────────────────────────────────────────────────
@dataclass
class DamInfo:
    name_en: str
    name_el: str
    capacity_m3: int
    capacity_mcm: float
    lat: float
    lng: float
    height: int
    year_built: int
    river_name_el: str
    type_el: str
    image_url: str
    wikipedia_url: str


@dataclass
class DamPercentage:
    dam_name_en: str
    percentage: float  # 0-1


@dataclass
class PercentageSnapshot:
    date: date
    dam_percentages: list[DamPercentage]
    total_percentage: float
    total_capacity_mcm: float


@dataclass
class DamStatistic:
    dam_name_en: str
    storage_mcm: float
    inflow_mcm: float


@dataclass
class DateStatistics:
    date: date
    dam_statistics: list[DamStatistic]


@dataclass
class MonthlyInflow:
    year: int
    period: str
    period_order: int
    inflow_mcm: float


@dataclass
class WaterEvent:
    name_en: str
    name_el: str
    event_type: str
    description: str
    date_from: date
    date_until: date


class UpstreamAPIError(Exception):
    """Raised when the upstream API is unreachable or returns an error."""
    pass


def _validate_url(raw: str) -> str:
    """Return raw if it is a safe https URL, otherwise return empty string."""
    stripped = raw.strip()
    return stripped if stripped.startswith("https://") else ""


# ── Date parsing helpers ──────────────────────────────────────────────────────
def _parse_api_date(raw: str) -> date:
    """Parse 'Feb 17, 2026 12:00:00 AM' → date(2026, 2, 17)"""
    return datetime.strptime(raw.strip(), "%b %d, %Y %I:%M:%S %p").date()


def _parse_ms_timestamp(ms: int) -> date:
    """Parse Unix timestamp in milliseconds → date."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def _parse_pct_entry(date_key: str, entry: dict) -> PercentageSnapshot:
    """
    Parse one entry from the timeseries percentages dict or a /percentages response.
    date_key is the "YYYY-MM-DD" key from timeseries; entry has 'date', 'damNamesToPercentage',
    'totalPercentage', 'totalCapacityInMCM'.
    """
    snap_date = date.fromisoformat(date_key) if date_key else _parse_api_date(entry["date"])
    dam_pcts = [
        DamPercentage(dam_name_en=name, percentage=float(pct))
        for name, pct in entry.get("damNamesToPercentage", {}).items()
    ]
    return PercentageSnapshot(
        date=snap_date,
        dam_percentages=dam_pcts,
        total_percentage=float(entry.get("totalPercentage", 0)),
        total_capacity_mcm=float(entry.get("totalCapacityInMCM", 0)),
    )


# ── API fetch functions ───────────────────────────────────────────────────────
async def fetch_dams() -> list[DamInfo]:
    """GET /dams → list of 17 DamInfo objects."""
    client = _get_client()
    try:
        resp = await client.get("/dams")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_dams failed: {exc}") from exc

    dams: list[DamInfo] = []
    for item in resp.json():
        cap_m3 = int(item.get("capacity", 0) or 0)
        dams.append(DamInfo(
            name_en=item["nameEn"],
            name_el=item.get("nameEl", ""),
            capacity_m3=cap_m3,
            capacity_mcm=round(cap_m3 / 1_000_000, 6),
            lat=float(item.get("lat", 0)),
            lng=float(item.get("lng", 0)),
            height=int(item.get("height", 0) or 0),
            year_built=int(item.get("yearOfConstruction", 0) or 0),
            river_name_el=item.get("riverNameEl", ""),
            type_el=item.get("typeEl", ""),
            image_url=_validate_url(item.get("imageUrl", "")),
            wikipedia_url=_validate_url(item.get("wikipediaUrl", "")),
        ))
    logger.info("Fetched %d dams", len(dams))
    return dams


async def fetch_percentages(target_date: date) -> PercentageSnapshot:
    """GET /percentages?date=YYYY-MM-DD → PercentageSnapshot."""
    client = _get_client()
    try:
        resp = await client.get("/percentages", params={"date": target_date.strftime("%Y-%m-%d")})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_percentages failed: {exc}") from exc

    payload = resp.json()
    return _parse_pct_entry(target_date.isoformat(), payload)


async def fetch_date_statistics(target_date: date) -> DateStatistics:
    """GET /date-statistics?date=YYYY-MM-DD → DateStatistics.
    Returns 18 dams (includes Agia Marina not in /dams).
    """
    client = _get_client()
    try:
        resp = await client.get("/date-statistics", params={"date": target_date.strftime("%Y-%m-%d")})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_date_statistics failed: {exc}") from exc

    payload = resp.json()
    storage = payload.get("storageInMCM", {})
    inflow = payload.get("inflowInMCM", {})
    all_dams = set(storage.keys()) | set(inflow.keys())

    stats = [
        DamStatistic(
            dam_name_en=name,
            storage_mcm=float(storage.get(name, 0)),
            inflow_mcm=float(inflow.get(name, 0)),
        )
        for name in all_dams
    ]
    return DateStatistics(date=target_date, dam_statistics=stats)


async def fetch_timeseries() -> list[PercentageSnapshot]:
    """GET /api/timeseries → ~133 PercentageSnapshot objects.
    Response is a dict: {percentages: {"YYYY-MM-DD": {...}}, dams: [...], ...}
    """
    client = _get_client()
    try:
        resp = await client.get("/timeseries")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_timeseries failed: {exc}") from exc

    payload = resp.json()
    pct_dict: dict = payload.get("percentages", {})
    snapshots: list[PercentageSnapshot] = []

    for date_key, entry in pct_dict.items():
        try:
            snapshots.append(_parse_pct_entry(date_key, entry))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping timeseries entry %s: %s", date_key, exc)

    # Sort chronologically for consistent chart rendering
    snapshots.sort(key=lambda s: s.date)
    logger.info("Fetched %d timeseries snapshots", len(snapshots))
    return snapshots


async def fetch_monthly_inflows() -> list[MonthlyInflow]:
    """GET /monthly-inflows → list of MonthlyInflow records."""
    client = _get_client()
    try:
        resp = await client.get("/monthly-inflows")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_monthly_inflows failed: {exc}") from exc

    inflows = [
        MonthlyInflow(
            year=int(item.get("year", 0)),
            period=item.get("period", ""),
            period_order=int(item.get("periodOrder", 0)),
            inflow_mcm=float(item.get("inflowInMCM", 0)),
        )
        for item in resp.json()
    ]
    logger.info("Fetched %d monthly inflow records", len(inflows))
    return inflows


async def fetch_events(date_from: date, date_until: date) -> list[WaterEvent]:
    """GET /events?from=YYYY-MM-DD&to=YYYY-MM-DD → list of WaterEvent.
    Note: event dates are Unix timestamps in milliseconds, not strings.
    """
    client = _get_client()
    try:
        resp = await client.get("/events", params={
            "from": date_from.strftime("%Y-%m-%d"),
            "to": date_until.strftime("%Y-%m-%d"),
        })
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise UpstreamAPIError(f"fetch_events failed: {exc}") from exc

    events: list[WaterEvent] = []
    for item in resp.json():
        try:
            events.append(WaterEvent(
                name_en=item.get("nameEn", ""),
                name_el=item.get("nameEl", ""),
                event_type=item.get("type", ""),        # field is "type" not "eventType"
                description=item.get("description", ""),
                date_from=_parse_ms_timestamp(item["from"]),    # millisecond timestamps
                date_until=_parse_ms_timestamp(item["until"]),
            ))
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Skipping event: %s", exc)

    logger.info("Fetched %d events", len(events))
    return events
