"""
Tests for the Czech Republic data provider.
Data source: CHMI (Czech Hydrometeorological Institute) — hydro.chmi.cz.
"""
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.czech import (
    CzechProvider,
    _CZECH_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def czech_provider() -> CzechProvider:
    client = httpx.AsyncClient(base_url="https://hydro.chmi.cz")
    return CzechProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_czech_provider_importable() -> None:
    from app.providers.czech import CzechProvider
    assert CzechProvider is not None


def test_czech_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = CzechProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15_reservoirs(czech_provider: CzechProvider) -> None:
    dams = await czech_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_largest_is_orlik(czech_provider: CzechProvider) -> None:
    dams = await czech_provider.fetch_dams()
    orlik = next(d for d in dams if d.name_en == "Orlik")
    assert orlik.capacity_mcm == 716.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(czech_provider: CzechProvider) -> None:
    dams = await czech_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} has lat=0"
        assert dam.lng != 0.0, f"{dam.name_en} has lng=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(czech_provider: CzechProvider) -> None:
    dams = await czech_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_czech_latitude_range(czech_provider: CzechProvider) -> None:
    """All dams should be within Czech Republic's bounding box."""
    dams = await czech_provider.fetch_dams()
    for dam in dams:
        assert 48.5 <= dam.lat <= 51.1, f"{dam.name_en} lat {dam.lat} outside Czech Republic"
        assert 12.0 <= dam.lng <= 18.9, f"{dam.name_en} lng {dam.lng} outside Czech Republic"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(czech_provider: CzechProvider) -> None:
    """name_en must be ASCII-safe for URL paths."""
    dams = await czech_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


# ── Mock HTML with fallback/default data ────────────────────────────────────
# The CHMI provider returns defaults (0.0 percentages) when upstream is unavailable.
# For testing, we provide a mock that simulates an HTTP error scenario and a
# successful fallback scenario.

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    """fetch_percentages returns a PercentageSnapshot with 15 dams even on fallback."""
    mock_response = httpx.Response(
        200,
        text="<html><body>No parseable data here</body></html>",
        request=httpx.Request("GET", "https://hydro.chmi.cz"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = CzechProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    """fetch_percentages raises UpstreamAPIError on HTTP 500."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://hydro.chmi.cz"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = CzechProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 14))


@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    """fetch_date_statistics returns DateStatistics with 15 dams."""
    mock_response = httpx.Response(
        200,
        text="<html><body>No parseable data here</body></html>",
        request=httpx.Request("GET", "https://hydro.chmi.cz"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = CzechProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(czech_provider: CzechProvider) -> None:
    result = await czech_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(czech_provider: CzechProvider) -> None:
    result = await czech_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(czech_provider: CzechProvider) -> None:
    result = await czech_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
