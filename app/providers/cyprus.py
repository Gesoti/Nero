"""
Cyprus data provider — fetches from the Water Development Department API.

Upstream: cyprus-water.appspot.com
API response shapes documented in the module docstring of the original api_client.py.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import httpx

from app.providers.base import (
    BaseProvider,
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


def _validate_url(raw: str) -> str:
    """Return raw if it is a safe https URL, otherwise return empty string."""
    stripped = raw.strip()
    return stripped if stripped.startswith("https://") else ""


def _parse_api_date(raw: str) -> date:
    """Parse 'Feb 17, 2026 12:00:00 AM' → date(2026, 2, 17)"""
    return datetime.strptime(raw.strip(), "%b %d, %Y %I:%M:%S %p").date()


def _parse_ms_timestamp(ms: int) -> date:
    """Parse Unix timestamp in milliseconds → date."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def _parse_pct_entry(date_key: str, entry: dict) -> PercentageSnapshot:
    """Parse one entry from the timeseries percentages dict or a /percentages response."""
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


class CyprusProvider(BaseProvider):
    """DataProvider implementation for the Cyprus Water Development Department API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client)

    async def fetch_dams(self) -> list[DamInfo]:
        """GET /dams → list of 17 DamInfo objects."""
        try:
            resp = await self._client.get("/dams")
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

    async def fetch_percentages(self, target_date: date) -> PercentageSnapshot:
        """GET /percentages?date=YYYY-MM-DD → PercentageSnapshot."""
        try:
            resp = await self._client.get("/percentages", params={"date": target_date.strftime("%Y-%m-%d")})
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamAPIError(f"fetch_percentages failed: {exc}") from exc

        payload = resp.json()
        return _parse_pct_entry(target_date.isoformat(), payload)

    async def fetch_date_statistics(self, target_date: date) -> DateStatistics:
        """GET /date-statistics?date=YYYY-MM-DD → DateStatistics."""
        try:
            resp = await self._client.get("/date-statistics", params={"date": target_date.strftime("%Y-%m-%d")})
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

    async def fetch_timeseries(self) -> list[PercentageSnapshot]:
        """GET /api/timeseries → sorted list of PercentageSnapshot objects."""
        try:
            resp = await self._client.get("/timeseries")
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

        snapshots.sort(key=lambda s: s.date)
        logger.info("Fetched %d timeseries snapshots", len(snapshots))
        return snapshots

    async def fetch_monthly_inflows(self) -> list[MonthlyInflow]:
        """GET /monthly-inflows → list of MonthlyInflow records."""
        try:
            resp = await self._client.get("/monthly-inflows")
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

    async def fetch_events(self, date_from: date, date_until: date) -> list[WaterEvent]:
        """GET /events?from=YYYY-MM-DD&to=YYYY-MM-DD → list of WaterEvent."""
        try:
            resp = await self._client.get("/events", params={
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
                    event_type=item.get("type", ""),
                    description=item.get("description", ""),
                    date_from=_parse_ms_timestamp(item["from"]),
                    date_until=_parse_ms_timestamp(item["until"]),
                ))
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Skipping event: %s", exc)

        logger.info("Fetched %d events", len(events))
        return events

