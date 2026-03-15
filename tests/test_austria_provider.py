"""
Tests for the Austria data provider.
Data source: ehyd.gv.at (Austrian Federal Hydrological Service).
For the MVP, the provider uses hardcoded dam metadata and falls back
gracefully when the upstream is unavailable.
"""
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.austria import (
    AustriaProvider,
    _AUSTRIA_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def austria_provider() -> AustriaProvider:
    client = httpx.AsyncClient(base_url="https://ehyd.gv.at")
    return AustriaProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_austria_provider_importable() -> None:
    from app.providers.austria import AustriaProvider
    assert AustriaProvider is not None


def test_austria_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = AustriaProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15_reservoirs(austria_provider: AustriaProvider) -> None:
    dams = await austria_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_largest_is_kolnbrein(austria_provider: AustriaProvider) -> None:
    dams = await austria_provider.fetch_dams()
    kolnbrein = next(d for d in dams if d.name_en == "Kolnbrein")
    assert kolnbrein.capacity_mcm == 200.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(austria_provider: AustriaProvider) -> None:
    dams = await austria_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} has lat=0"
        assert dam.lng != 0.0, f"{dam.name_en} has lng=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(austria_provider: AustriaProvider) -> None:
    dams = await austria_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_austria_latitude_range(austria_provider: AustriaProvider) -> None:
    """All dams should be within Austria's bounding box."""
    dams = await austria_provider.fetch_dams()
    for dam in dams:
        assert 46.3 <= dam.lat <= 48.9, f"{dam.name_en} lat {dam.lat} outside Austria"
        assert 9.5 <= dam.lng <= 17.2, f"{dam.name_en} lng {dam.lng} outside Austria"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(austria_provider: AustriaProvider) -> None:
    """name_en must be ASCII-safe for URL paths."""
    dams = await austria_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

# Austria's eHYD does not expose a simple parseable API, so fetch_percentages
# falls back to returning 0.0 for all dams on any HTTP response.
# We test that the method returns a valid PercentageSnapshot regardless.

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    """fetch_percentages must return a valid PercentageSnapshot with 15 entries."""
    mock_response = httpx.Response(
        200,
        text="<html><body>No parseable data here</body></html>",
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = AustriaProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    """HTTP errors must raise UpstreamAPIError."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = AustriaProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 14))


# ── fetch_date_statistics tests (mocked HTTP) ────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    """fetch_date_statistics must return a DateStatistics with 15 entries."""
    mock_response = httpx.Response(
        200,
        text="<html><body>No parseable data here</body></html>",
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = AustriaProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


# ── Stub return methods ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(austria_provider: AustriaProvider) -> None:
    result = await austria_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(austria_provider: AustriaProvider) -> None:
    result = await austria_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(austria_provider: AustriaProvider) -> None:
    result = await austria_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
