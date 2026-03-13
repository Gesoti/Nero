"""
TDD tests for G1: sync.py refactoring to accept explicit provider + db_path arguments.
"""
from __future__ import annotations

import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.providers.base import (
    DateStatistics,
    MonthlyInflow,
    PercentageSnapshot,
    DamPercentage,
    WaterEvent,
)


def _make_mock_provider() -> AsyncMock:
    """Create a mock DataProvider with all required methods."""
    provider = AsyncMock()
    provider.fetch_dams.return_value = []
    provider.fetch_timeseries.return_value = []
    provider.fetch_monthly_inflows.return_value = []
    provider.fetch_events.return_value = []
    provider.fetch_date_statistics.return_value = DateStatistics(
        date=date.today(), dam_statistics=[]
    )
    provider.fetch_percentages.return_value = PercentageSnapshot(
        date=date.today(), dam_percentages=[], total_percentage=0.0, total_capacity_mcm=0.0
    )
    return provider


@pytest.mark.asyncio
async def test_initial_seed_accepts_provider_argument(in_memory_db: None) -> None:
    """initial_seed() must accept explicit provider and db_path args."""
    from app.sync import initial_seed

    provider = _make_mock_provider()
    await initial_seed(provider=provider, db_path=":memory:")
    provider.fetch_dams.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_sync_accepts_provider_argument(in_memory_db: None) -> None:
    """incremental_sync() must accept explicit provider and db_path args."""
    from app.sync import incremental_sync

    provider = _make_mock_provider()
    await incremental_sync(provider=provider, db_path=":memory:")
    provider.fetch_percentages.assert_awaited_once()


def test_sync_does_not_import_api_client() -> None:
    """sync.py must not directly import from app.api_client."""
    import importlib
    import app.sync as sync_module

    importlib.reload(sync_module)
    source_file = sys.modules["app.sync"].__file__
    assert source_file is not None
    with open(source_file) as f:
        source = f.read()
    assert "from app.api_client" not in source
    assert "import app.api_client" not in source


def test_enabled_countries_config_default() -> None:
    """Settings must have an enabled_countries field defaulting to 'cy'."""
    from app.config import Settings

    s = Settings()
    assert s.get_enabled_countries() == ["cy"]


def test_enabled_countries_config_parse_csv() -> None:
    """WL_ENABLED_COUNTRIES='cy,gr' must parse to ['cy', 'gr']."""
    from app.config import Settings

    with patch.dict("os.environ", {"WL_ENABLED_COUNTRIES": "cy,gr"}):
        s = Settings()
        assert s.get_enabled_countries() == ["cy", "gr"]
