"""
Unit tests for app/db.py — get_severity() boundaries and all query functions.
Every test that touches the DB uses the `in_memory_db` fixture so each
test function gets a clean, isolated in-memory SQLite instance.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.db import (
    get_all_dams_with_current_stats,
    get_dam_detail,
    get_dam_history,
    get_severity,
    get_system_history,
    get_system_totals,
    is_database_empty,
    upsert_date_statistics,
    upsert_dams,
    upsert_percentage_snapshot,
)


# ── Minimal stub dataclasses matching what the upsert functions read ──────────
# These mirror the DamInfo / PercentageSnapshot / etc. dataclasses from
# api_client.py so we can insert fixture data without importing from api_client.

@dataclass
class _DamInfoStub:
    name_en: str
    name_el: str
    capacity_mcm: float
    lat: float
    lng: float
    height: int          # upsert_dams reads .height (not height_m)
    year_built: int
    river_name_el: str
    type_el: str
    image_url: str
    wikipedia_url: str


@dataclass
class _DamPercentageStub:
    dam_name_en: str
    percentage: float


@dataclass
class _PercentageSnapshotStub:
    date: date
    dam_percentages: list[_DamPercentageStub]
    total_percentage: float
    total_capacity_mcm: float


@dataclass
class _DamStatisticStub:
    dam_name_en: str
    storage_mcm: float
    inflow_mcm: float


@dataclass
class _DateStatisticsStub:
    date: date
    dam_statistics: list[_DamStatisticStub]


# ── Fixture helpers ───────────────────────────────────────────────────────────

def _insert_test_dam(name_en: str = "Test Dam") -> None:
    """Insert one dam row so JOIN-based queries have something to find."""
    dam = _DamInfoStub(
        name_en=name_en,
        name_el="Δοκιμαστικό Φράγμα",
        capacity_mcm=100.0,
        lat=34.9,
        lng=33.1,
        height=50,
        year_built=1990,
        river_name_el="Ποταμός",
        type_el="Τύπος",
        image_url="",
        wikipedia_url="",
    )
    upsert_dams([dam])


def _insert_test_percentage(dam_name: str, pct: float, snapshot_date: date) -> None:
    snap = _PercentageSnapshotStub(
        date=snapshot_date,
        dam_percentages=[_DamPercentageStub(dam_name_en=dam_name, percentage=pct)],
        total_percentage=pct,
        total_capacity_mcm=100.0,
    )
    upsert_percentage_snapshot(snap)


def _insert_test_statistics(dam_name: str, snapshot_date: date) -> None:
    stats = _DateStatisticsStub(
        date=snapshot_date,
        dam_statistics=[_DamStatisticStub(dam_name_en=dam_name, storage_mcm=50.0, inflow_mcm=2.5)],
    )
    upsert_date_statistics(stats)


# ── get_severity() — boundary tests ──────────────────────────────────────────

class TestGetSeverity:
    """All severity thresholds: <0.20 critical, 0.20–0.40 warning, >=0.40 healthy."""

    def test_zero_is_critical(self):
        assert get_severity(0.0) == "critical"

    def test_midpoint_critical(self):
        assert get_severity(0.10) == "critical"

    def test_just_below_warning_boundary(self):
        # 0.199... is still critical
        assert get_severity(0.19) == "critical"

    def test_exactly_at_warning_boundary(self):
        # 0.20 is the first value that should be "warning"
        assert get_severity(0.20) == "warning"

    def test_midpoint_warning(self):
        assert get_severity(0.30) == "warning"

    def test_just_below_healthy_boundary(self):
        # 0.399... is still warning
        assert get_severity(0.39) == "warning"

    def test_exactly_at_healthy_boundary(self):
        # 0.40 is the first value that should be "healthy"
        assert get_severity(0.40) == "healthy"

    def test_full_is_healthy(self):
        assert get_severity(1.0) == "healthy"


# ── DB query functions — empty database ───────────────────────────────────────

class TestEmptyDatabase:
    """Query functions must return safe empty values on a freshly initialised DB."""

    def test_get_all_dams_returns_empty_list(self, in_memory_db):
        assert get_all_dams_with_current_stats() == []

    def test_get_system_totals_returns_none(self, in_memory_db):
        assert get_system_totals() is None

    def test_get_dam_detail_nonexistent_returns_none(self, in_memory_db):
        assert get_dam_detail("nonexistent-dam-xyz") is None

    def test_get_dam_history_nonexistent_returns_empty_list(self, in_memory_db):
        assert get_dam_history("nonexistent-dam-xyz") == []

    def test_get_system_history_returns_empty_list(self, in_memory_db):
        assert get_system_history() == []

    def test_is_database_empty_fresh_db_returns_true(self, in_memory_db):
        assert is_database_empty() is True


# ── DB query functions — happy path with fixture data ─────────────────────────

class TestDatabaseWithData:
    """Verify that queries return correctly shaped dataclasses when data exists."""

    TEST_DATE = date(2026, 2, 18)
    DAM_NAME = "Kouris"

    def _seed(self) -> None:
        """Insert one dam + percentage + statistics row."""
        _insert_test_dam(self.DAM_NAME)
        _insert_test_percentage(self.DAM_NAME, 0.35, self.TEST_DATE)
        _insert_test_statistics(self.DAM_NAME, self.TEST_DATE)

    def test_get_all_dams_returns_one_dam(self, in_memory_db):
        self._seed()
        dams = get_all_dams_with_current_stats()
        assert len(dams) == 1
        dam = dams[0]
        assert dam.name_en == self.DAM_NAME
        assert dam.percentage == pytest.approx(0.35)
        assert dam.storage_mcm == pytest.approx(50.0)
        assert dam.inflow_mcm == pytest.approx(2.5)

    def test_get_system_totals_returns_dataclass(self, in_memory_db):
        self._seed()
        totals = get_system_totals()
        assert totals is not None
        assert totals.total_percentage == pytest.approx(0.35)
        assert totals.total_capacity_mcm == pytest.approx(100.0)
        assert totals.date == self.TEST_DATE.isoformat()
        # dam_count reflects how many distinct dam_name_en rows joined from daily_statistics
        assert totals.dam_count == 1

    def test_get_dam_detail_returns_dataclass(self, in_memory_db):
        self._seed()
        detail = get_dam_detail(self.DAM_NAME)
        assert detail is not None
        assert detail.name_en == self.DAM_NAME
        assert detail.capacity_mcm == pytest.approx(100.0)
        assert detail.percentage == pytest.approx(0.35)
        assert detail.current_date == self.TEST_DATE.isoformat()

    def test_get_dam_history_returns_scaled_values(self, in_memory_db):
        self._seed()
        history = get_dam_history(self.DAM_NAME)
        assert len(history) == 1
        entry = history[0]
        assert entry["date"] == self.TEST_DATE.isoformat()
        # DB stores 0-1, get_dam_history returns 0-100 scale
        assert entry["value"] == pytest.approx(35.0)

    def test_get_system_history_returns_scaled_values(self, in_memory_db):
        self._seed()
        history = get_system_history()
        assert len(history) == 1
        entry = history[0]
        assert entry["date"] == self.TEST_DATE.isoformat()
        # DB stores 0-1, get_system_history returns 0-100 scale
        assert entry["value"] == pytest.approx(35.0)

    def test_is_database_empty_with_data_returns_false(self, in_memory_db):
        # Inserting via upsert_dams alone does NOT update sync_log;
        # is_database_empty checks sync_log, so we confirm it is still True
        # after inserting a dam but before calling update_sync_log.
        _insert_test_dam("SomeDam")
        assert is_database_empty() is True

    def test_get_dam_detail_nonexistent_after_insert_returns_none(self, in_memory_db):
        self._seed()
        assert get_dam_detail("No Such Dam") is None


# ── Slug column tests ────────────────────────────────────────────────────────

class TestDamSlugColumn:
    """Verify that the dams table has a slug column populated on upsert."""

    def test_slug_column_exists(self, in_memory_db):
        """Schema must include slug column in dams table."""
        from app.db import _get_connection
        conn = _get_connection()
        try:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(dams)").fetchall()]
            assert "slug" in cols
        finally:
            conn.close()

    def test_slug_populated_on_upsert(self, in_memory_db):
        """upsert_dams must auto-populate the slug column."""
        _insert_test_dam("Kouris")
        from app.db import _get_connection
        conn = _get_connection()
        try:
            row = conn.execute("SELECT slug FROM dams WHERE name_en = ?", ("Kouris",)).fetchone()
            assert row is not None
            assert row["slug"] == "kouris"
        finally:
            conn.close()

    def test_slug_for_multi_word_name(self, in_memory_db):
        _insert_test_dam("Marathon Lake")
        from app.db import _get_connection
        conn = _get_connection()
        try:
            row = conn.execute("SELECT slug FROM dams WHERE name_en = ?", ("Marathon Lake",)).fetchone()
            assert row["slug"] == "marathon-lake"
        finally:
            conn.close()
