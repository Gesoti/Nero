"""
Tests for the Italy data provider.
Data source: OpenData Sicilia GitHub CSV (opendatasicilia/emergenza-idrica-sicilia).
Covers 13 Sicilian reservoirs.
"""
import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.italy import (
    ItalyProvider,
    _ITALY_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def italy_provider() -> ItalyProvider:
    client = httpx.AsyncClient(base_url="https://raw.githubusercontent.com")
    return ItalyProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_italy_provider_importable() -> None:
    from app.providers.italy import ItalyProvider
    assert ItalyProvider is not None


def test_italy_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = ItalyProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_13_reservoirs(italy_provider: ItalyProvider) -> None:
    dams = await italy_provider.fetch_dams()
    assert len(dams) == 13


@pytest.mark.asyncio
async def test_fetch_dams_largest_is_pozzillo(italy_provider: ItalyProvider) -> None:
    dams = await italy_provider.fetch_dams()
    pozzillo = next(d for d in dams if d.name_en == "Pozzillo")
    assert pozzillo.capacity_mcm == 150.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(italy_provider: ItalyProvider) -> None:
    dams = await italy_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} has lat=0"
        assert dam.lng != 0.0, f"{dam.name_en} has lng=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(italy_provider: ItalyProvider) -> None:
    dams = await italy_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_sicily_latitude_range(italy_provider: ItalyProvider) -> None:
    """All dams should be within Sicily's bounding box."""
    dams = await italy_provider.fetch_dams()
    for dam in dams:
        assert 36.6 <= dam.lat <= 38.3, f"{dam.name_en} lat {dam.lat} outside Sicily"
        assert 12.4 <= dam.lng <= 15.7, f"{dam.name_en} lng {dam.lng} outside Sicily"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(italy_provider: ItalyProvider) -> None:
    """name_en must be ASCII-safe for URL paths."""
    dams = await italy_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


# ── Mock CSV for HTTP tests ──────────────────────────────────────────────────

# Realistic mock CSV matching the OpenData Sicilia format.
# volume_autorizzato_mc is in cubic metres; volume_invasato_mc is current storage.
_MOCK_CSV = """nome_diga,data,volume_autorizzato_mc,volume_invasato_mc
Ancipa,2026-03-14,30400000,15200000
Pozzillo,2026-03-14,150000000,120000000
Ogliastro,2026-03-14,110000000,55000000
Prizzi,2026-03-14,10000000,4000000
Fanaco,2026-03-14,21000000,10500000
Gammauta,2026-03-14,7000000,3500000
Leone,2026-03-14,7000000,2100000
Garcia,2026-03-14,64000000,32000000
Piana degli Albanesi,2026-03-14,31000000,15500000
Scanzano,2026-03-14,2600000,1300000
Rosamarina,2026-03-14,100000000,50000000
Cimia,2026-03-14,12000000,6000000
Ragoleto,2026-03-14,2500000,1250000
"""

_MOCK_CSV_PARTIAL = """nome_diga,data,volume_autorizzato_mc,volume_invasato_mc
Ancipa,2026-03-14,30400000,15200000
"""


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 13


@pytest.mark.asyncio
async def test_fetch_percentages_pozzillo_pct() -> None:
    """Pozzillo at 120,000,000 m³ / 150,000,000 m³ capacity = 0.80"""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    pozzillo = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Pozzillo")
    assert abs(pozzillo.percentage - 0.80) < 0.01


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 14))


@pytest.mark.asyncio
async def test_fetch_percentages_handles_missing_dam() -> None:
    """If upstream data lacks a dam from our hardcoded list, use 0.0 for that dam."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV_PARTIAL,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 13
    # Ancipa should have data
    ancipa = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Ancipa")
    assert ancipa.percentage > 0
    # Others should be 0
    pozzillo = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Pozzillo")
    assert pozzillo.percentage == 0.0


# ── fetch_date_statistics tests (mocked HTTP) ────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 13
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


@pytest.mark.asyncio
async def test_fetch_date_statistics_pozzillo_volume() -> None:
    """Pozzillo volume_invasato = 120,000,000 m³ = 120.0 hm³."""
    mock_response = httpx.Response(
        200,
        text=_MOCK_CSV,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = ItalyProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    pozzillo = next(s for s in result.dam_statistics if s.dam_name_en == "Pozzillo")
    assert abs(pozzillo.storage_mcm - 120.0) < 0.1


# ── Empty-return methods ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(italy_provider: ItalyProvider) -> None:
    result = await italy_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(italy_provider: ItalyProvider) -> None:
    result = await italy_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(italy_provider: ItalyProvider) -> None:
    result = await italy_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
