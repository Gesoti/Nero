"""
Tests for the Finland data provider.
Data source: SYKE (Finnish Environment Institute) Hydrology OData API.
Finland's 'dams' are regulated natural lakes — some of the largest water
bodies in Northern Europe.
"""
import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.finland import (
    FinlandProvider,
    _FINLAND_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def finland_provider() -> FinlandProvider:
    client = httpx.AsyncClient(base_url="http://rajapinnat.ymparisto.fi")
    return FinlandProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_finland_provider_importable() -> None:
    from app.providers.finland import FinlandProvider
    assert FinlandProvider is not None


def test_finland_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="http://example.com")
    provider = FinlandProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15_reservoirs(finland_provider: FinlandProvider) -> None:
    dams = await finland_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_largest_is_inarijarvi(finland_provider: FinlandProvider) -> None:
    dams = await finland_provider.fetch_dams()
    inari = next(d for d in dams if d.name_en == "Inarijarvi")
    assert inari.capacity_mcm == 15000.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(finland_provider: FinlandProvider) -> None:
    dams = await finland_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} has lat=0"
        assert dam.lng != 0.0, f"{dam.name_en} has lng=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(finland_provider: FinlandProvider) -> None:
    dams = await finland_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_finland_bounding_box(finland_provider: FinlandProvider) -> None:
    """All regulated lakes should fall within Finland's geographic bounding box."""
    dams = await finland_provider.fetch_dams()
    for dam in dams:
        assert 60.0 <= dam.lat <= 70.2, f"{dam.name_en} lat {dam.lat} outside Finland"
        assert 20.5 <= dam.lng <= 31.6, f"{dam.name_en} lng {dam.lng} outside Finland"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(finland_provider: FinlandProvider) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await finland_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_saimaa_present(finland_provider: FinlandProvider) -> None:
    """Saimaa — Finland's largest lake — must be in the list."""
    dams = await finland_provider.fetch_dams()
    names = [d.name_en for d in dams]
    assert "Saimaa" in names


@pytest.mark.asyncio
async def test_fetch_dams_paijanne_present(finland_provider: FinlandProvider) -> None:
    dams = await finland_provider.fetch_dams()
    names = [d.name_en for d in dams]
    assert "Paijanne" in names


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

# Minimal mock XML that matches what SYKE OData returns for water level observations.
# Real endpoint: /api/Hydrologiarajapinta/1.1/Havainto
# Returns Atom feed with <d:Arvo> (value in cm) and <d:Aika> (timestamp).
_MOCK_SYKE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <title type="text">Havainto</title>
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:Arvo>120</d:Arvo>
        <d:Aika>2026-03-14T00:00:00</d:Aika>
      </m:properties>
    </content>
  </entry>
</feed>
"""


@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot_with_15_entries() -> None:
    """On a valid API response, fetch_percentages returns a snapshot for all 15 dams."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_SYKE_XML,
        request=httpx.Request("GET", "http://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = FinlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_percentages_in_valid_range() -> None:
    """All returned percentages must be in [0, 1] range."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_SYKE_XML,
        request=httpx.Request("GET", "http://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = FinlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    for dp in result.dam_percentages:
        assert 0.0 <= dp.percentage <= 1.0, (
            f"{dp.dam_name_en} percentage {dp.percentage} outside [0, 1]"
        )


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_http_error() -> None:
    """On HTTP error, fetch_percentages returns zero-fill defaults (does not raise)."""
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "http://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = FinlandProvider(client=client)
    # Should NOT raise — graceful fallback to 0.0 for all dams
    result = await provider.fetch_percentages(date(2026, 3, 14))
    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15
    for dp in result.dam_percentages:
        assert dp.percentage == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, fetch_percentages returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = FinlandProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))
    assert isinstance(result, PercentageSnapshot)
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target() -> None:
    """Snapshot date must match the requested target date."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_SYKE_XML,
        request=httpx.Request("GET", "http://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = FinlandProvider(client=client)
    target = date(2026, 3, 14)
    result = await provider.fetch_percentages(target)
    assert result.date == target


# ── fetch_date_statistics tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats_for_all_dams() -> None:
    mock_response = httpx.Response(
        200,
        text=_MOCK_SYKE_XML,
        request=httpx.Request("GET", "http://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = FinlandProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(finland_provider: FinlandProvider) -> None:
    result = await finland_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(finland_provider: FinlandProvider) -> None:
    result = await finland_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(finland_provider: FinlandProvider) -> None:
    result = await finland_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
