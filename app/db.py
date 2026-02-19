"""
SQLite database layer using WAL mode for concurrent reads during scheduler writes.
All query functions return typed dataclasses; connections are opened per-call and
closed immediately to avoid holding locks.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


# ── DB result dataclasses ─────────────────────────────────────────────────────
@dataclass
class DamOverview:
    name_en: str
    name_el: str
    capacity_mcm: float
    percentage: float
    storage_mcm: float
    inflow_mcm: float
    lat: float
    lng: float


@dataclass
class SystemTotals:
    total_percentage: float
    total_capacity_mcm: float
    total_storage_mcm: float
    total_inflow_mcm: float
    date: str
    dam_count: int


@dataclass
class DamDetail:
    name_en: str
    name_el: str
    capacity_mcm: float
    lat: float
    lng: float
    height_m: int
    year_built: int
    river_name_el: str
    type_el: str
    image_url: str
    wikipedia_url: str
    percentage: float
    storage_mcm: float
    inflow_mcm: float
    current_date: str


# ── Severity helper ───────────────────────────────────────────────────────────
def get_severity(percentage: float) -> str:
    """
    Map a 0-1 fill percentage to a severity label.
    Thresholds are domain-defined: <20% is crisis territory for Cyprus reservoirs.
    """
    if percentage < 0.20:
        return "critical"
    if percentage < 0.40:
        return "warning"
    return "healthy"


# ── Connection factory ────────────────────────────────────────────────────────
def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    # WAL allows concurrent reads while the scheduler performs writes
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema initialisation ─────────────────────────────────────────────────────
def init_database() -> None:
    """Create all tables and indexes if they do not already exist."""
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dams (
                name_en       TEXT PRIMARY KEY,
                name_el       TEXT NOT NULL,
                capacity_mcm  REAL NOT NULL,
                lat           REAL NOT NULL,
                lng           REAL NOT NULL,
                height_m      INTEGER NOT NULL,
                year_built    INTEGER NOT NULL,
                river_name_el TEXT NOT NULL DEFAULT '',
                type_el       TEXT NOT NULL DEFAULT '',
                image_url     TEXT NOT NULL DEFAULT '',
                wikipedia_url TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS daily_percentages (
                date        TEXT NOT NULL,
                dam_name_en TEXT NOT NULL,
                percentage  REAL NOT NULL,
                PRIMARY KEY (date, dam_name_en)
            );
            CREATE INDEX IF NOT EXISTS idx_percentages_dam
                ON daily_percentages(dam_name_en, date);
            CREATE INDEX IF NOT EXISTS idx_percentages_date
                ON daily_percentages(date);

            CREATE TABLE IF NOT EXISTS daily_totals (
                date               TEXT PRIMARY KEY,
                total_percentage   REAL NOT NULL,
                total_capacity_mcm REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_statistics (
                date        TEXT NOT NULL,
                dam_name_en TEXT NOT NULL,
                storage_mcm REAL NOT NULL,
                inflow_mcm  REAL NOT NULL,
                PRIMARY KEY (date, dam_name_en)
            );
            CREATE INDEX IF NOT EXISTS idx_stats_dam
                ON daily_statistics(dam_name_en, date);

            CREATE TABLE IF NOT EXISTS monthly_inflows (
                year         INTEGER NOT NULL,
                period       TEXT NOT NULL,
                period_order INTEGER NOT NULL,
                inflow_mcm   REAL NOT NULL,
                PRIMARY KEY (year, period)
            );

            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name_en    TEXT NOT NULL,
                name_el    TEXT NOT NULL DEFAULT '',
                event_type TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                date_from  TEXT NOT NULL,
                date_until TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_events_unique
                ON events(name_en, event_type, date_from);

            CREATE TABLE IF NOT EXISTS sync_log (
                data_type  TEXT PRIMARY KEY,
                last_synced TEXT NOT NULL,
                last_date  TEXT NOT NULL DEFAULT ''
            );
        """)
    conn.close()
    logger.info("Database initialised at %s", settings.db_path)


def is_database_empty() -> bool:
    """Return True if sync_log has no rows (first-run detection)."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM sync_log").fetchone()
        return row["cnt"] == 0
    finally:
        conn.close()


# ── Upsert functions (called by sync.py) ─────────────────────────────────────
def upsert_dams(dams) -> None:  # type: list[DamInfo] — imported lazily to avoid circular
    conn = _get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO dams
                (name_en, name_el, capacity_mcm, lat, lng, height_m, year_built,
                 river_name_el, type_el, image_url, wikipedia_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name_en) DO UPDATE SET
                name_el=excluded.name_el,
                capacity_mcm=excluded.capacity_mcm,
                lat=excluded.lat, lng=excluded.lng,
                height_m=excluded.height_m,
                year_built=excluded.year_built,
                river_name_el=excluded.river_name_el,
                type_el=excluded.type_el,
                image_url=excluded.image_url,
                wikipedia_url=excluded.wikipedia_url
            """,
            [
                (d.name_en, d.name_el, d.capacity_mcm, d.lat, d.lng,
                 d.height, d.year_built, d.river_name_el, d.type_el,
                 d.image_url, d.wikipedia_url)
                for d in dams
            ],
        )
    conn.close()
    logger.debug("Upserted %d dams", len(dams))


def upsert_percentage_snapshot(snapshot) -> None:
    date_str = snapshot.date.isoformat()
    conn = _get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO daily_percentages (date, dam_name_en, percentage)
            VALUES (?, ?, ?)
            ON CONFLICT(date, dam_name_en) DO UPDATE SET percentage=excluded.percentage
            """,
            [(date_str, dp.dam_name_en, dp.percentage) for dp in snapshot.dam_percentages],
        )
        conn.execute(
            """
            INSERT INTO daily_totals (date, total_percentage, total_capacity_mcm)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_percentage=excluded.total_percentage,
                total_capacity_mcm=excluded.total_capacity_mcm
            """,
            (date_str, snapshot.total_percentage, snapshot.total_capacity_mcm),
        )
    conn.close()


def upsert_date_statistics(stats) -> None:
    date_str = stats.date.isoformat()
    conn = _get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO daily_statistics (date, dam_name_en, storage_mcm, inflow_mcm)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date, dam_name_en) DO UPDATE SET
                storage_mcm=excluded.storage_mcm,
                inflow_mcm=excluded.inflow_mcm
            """,
            [(date_str, s.dam_name_en, s.storage_mcm, s.inflow_mcm) for s in stats.dam_statistics],
        )
    conn.close()


def upsert_monthly_inflows(inflows) -> None:
    conn = _get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO monthly_inflows (year, period, period_order, inflow_mcm)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(year, period) DO UPDATE SET
                period_order=excluded.period_order,
                inflow_mcm=excluded.inflow_mcm
            """,
            [(i.year, i.period, i.period_order, i.inflow_mcm) for i in inflows],
        )
    conn.close()


def upsert_events(events) -> None:
    conn = _get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO events (name_en, name_el, event_type, description, date_from, date_until)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name_en, event_type, date_from) DO UPDATE SET
                name_el=excluded.name_el,
                description=excluded.description,
                date_until=excluded.date_until
            """,
            [
                (e.name_en, e.name_el, e.event_type, e.description,
                 e.date_from.isoformat(), e.date_until.isoformat())
                for e in events
            ],
        )
    conn.close()


def update_sync_log(data_type: str, last_date: date) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO sync_log (data_type, last_synced, last_date)
            VALUES (?, ?, ?)
            ON CONFLICT(data_type) DO UPDATE SET
                last_synced=excluded.last_synced,
                last_date=excluded.last_date
            """,
            (data_type, now, last_date.isoformat()),
        )
    conn.close()


# ── Query functions (called by route handlers) ────────────────────────────────
def get_all_dams_with_current_stats() -> list[DamOverview]:
    """
    Join dams with their most recent percentage and statistics.
    LEFT JOIN naturally excludes Agia Marina (stats only, no dams row).
    """
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT
                d.name_en, d.name_el, d.capacity_mcm, d.lat, d.lng,
                COALESCE(dp.percentage, 0) AS percentage,
                COALESCE(ds.storage_mcm, 0) AS storage_mcm,
                COALESCE(ds.inflow_mcm, 0) AS inflow_mcm
            FROM dams d
            LEFT JOIN daily_percentages dp
                ON dp.dam_name_en = d.name_en
                AND dp.date = (
                    SELECT MAX(date) FROM daily_percentages WHERE dam_name_en = d.name_en
                )
            LEFT JOIN daily_statistics ds
                ON ds.dam_name_en = d.name_en
                AND ds.date = (
                    SELECT MAX(date) FROM daily_statistics WHERE dam_name_en = d.name_en
                )
            ORDER BY d.capacity_mcm DESC
        """).fetchall()
        return [
            DamOverview(
                name_en=r["name_en"], name_el=r["name_el"],
                capacity_mcm=r["capacity_mcm"],
                percentage=r["percentage"],
                storage_mcm=r["storage_mcm"],
                inflow_mcm=r["inflow_mcm"],
                lat=r["lat"], lng=r["lng"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_system_totals() -> SystemTotals | None:
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT
                dt.date,
                dt.total_percentage,
                dt.total_capacity_mcm,
                COALESCE(SUM(ds.storage_mcm), 0) AS total_storage_mcm,
                COALESCE(SUM(ds.inflow_mcm), 0) AS total_inflow_mcm,
                COUNT(DISTINCT ds.dam_name_en) AS dam_count
            FROM daily_totals dt
            LEFT JOIN daily_statistics ds ON ds.date = dt.date
            WHERE dt.date = (SELECT MAX(date) FROM daily_totals)
            GROUP BY dt.date
        """).fetchone()
        if row is None:
            return None
        return SystemTotals(
            total_percentage=row["total_percentage"],
            total_capacity_mcm=row["total_capacity_mcm"],
            total_storage_mcm=row["total_storage_mcm"],
            total_inflow_mcm=row["total_inflow_mcm"],
            date=row["date"],
            dam_count=row["dam_count"],
        )
    finally:
        conn.close()


def get_dam_detail(name_en: str) -> DamDetail | None:
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT
                d.name_en, d.name_el, d.capacity_mcm, d.lat, d.lng,
                d.height_m, d.year_built, d.river_name_el, d.type_el,
                d.image_url, d.wikipedia_url,
                COALESCE(dp.percentage, 0) AS percentage,
                COALESCE(ds.storage_mcm, 0) AS storage_mcm,
                COALESCE(ds.inflow_mcm, 0) AS inflow_mcm,
                COALESCE(dp.date, '') AS current_date
            FROM dams d
            LEFT JOIN daily_percentages dp
                ON dp.dam_name_en = d.name_en
                AND dp.date = (
                    SELECT MAX(date) FROM daily_percentages WHERE dam_name_en = d.name_en
                )
            LEFT JOIN daily_statistics ds
                ON ds.dam_name_en = d.name_en
                AND ds.date = (
                    SELECT MAX(date) FROM daily_statistics WHERE dam_name_en = d.name_en
                )
            WHERE d.name_en = ?
        """, (name_en,)).fetchone()
        if row is None:
            return None
        return DamDetail(
            name_en=row["name_en"], name_el=row["name_el"],
            capacity_mcm=row["capacity_mcm"],
            lat=row["lat"], lng=row["lng"],
            height_m=row["height_m"], year_built=row["year_built"],
            river_name_el=row["river_name_el"], type_el=row["type_el"],
            image_url=row["image_url"], wikipedia_url=row["wikipedia_url"],
            percentage=row["percentage"],
            storage_mcm=row["storage_mcm"],
            inflow_mcm=row["inflow_mcm"],
            current_date=row["current_date"],
        )
    finally:
        conn.close()


def get_system_history() -> list[dict]:
    """System percentage history as chart-ready dicts (0-100 scale)."""
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT date, total_percentage AS value
            FROM daily_totals
            ORDER BY date ASC
        """).fetchall()
        return [{"date": r["date"], "value": round(r["value"] * 100, 2)} for r in rows]
    finally:
        conn.close()


def get_dam_history(name_en: str) -> list[dict]:
    """Per-dam percentage history as chart-ready dicts (0-100 scale)."""
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT date, percentage AS value
            FROM daily_percentages
            WHERE dam_name_en = ?
            ORDER BY date ASC
        """, (name_en,)).fetchall()
        return [{"date": r["date"], "value": round(r["value"] * 100, 2)} for r in rows]
    finally:
        conn.close()


def get_last_sync_time() -> str | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT last_synced FROM sync_log ORDER BY last_synced DESC LIMIT 1"
        ).fetchone()
        return row["last_synced"] if row else None
    finally:
        conn.close()
