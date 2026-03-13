import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.greece import GreeceProvider, _parse_eydap_volume
from app.providers.base import DataProvider, PercentageSnapshot, DateStatistics, UpstreamAPIError


@pytest.fixture
def greece_provider() -> GreeceProvider:
    client = httpx.AsyncClient(base_url="https://opendata-api-eydap.growthfund.gr")
    return GreeceProvider(client=client)


def test_greece_provider_importable() -> None:
    from app.providers.greece import GreeceProvider
    assert GreeceProvider is not None


def test_greece_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = GreeceProvider(client=client)
    assert isinstance(provider, DataProvider)


@pytest.mark.asyncio
async def test_fetch_dams_returns_four_reservoirs(greece_provider: GreeceProvider) -> None:
    dams = await greece_provider.fetch_dams()
    assert len(dams) == 4


@pytest.mark.asyncio
async def test_fetch_dams_mornos_capacity_is_780(greece_provider: GreeceProvider) -> None:
    dams = await greece_provider.fetch_dams()
    mornos = next(d for d in dams if d.name_en == "Mornos")
    assert mornos.capacity_mcm == 780.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(greece_provider: GreeceProvider) -> None:
    dams = await greece_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0
        assert dam.lng != 0.0


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty_list(greece_provider: GreeceProvider) -> None:
    result = await greece_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty_list(greece_provider: GreeceProvider) -> None:
    result = await greece_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []


# ── Volume parser tests ────────────────────────────────────────────────────────

def test_parse_eydap_volume_dots_format() -> None:
    assert _parse_eydap_volume("93.063.000") == 93063000


def test_parse_eydap_volume_plain_int() -> None:
    assert _parse_eydap_volume("5000000") == 5000000


def test_parse_eydap_volume_zero() -> None:
    assert _parse_eydap_volume("0") == 0


def test_parse_eydap_volume_large() -> None:
    assert _parse_eydap_volume("780.000.000") == 780000000


# ── fetch_percentages tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    mock_response = httpx.Response(
        200,
        json={
            "Date": "12-03-2026",
            "Eyinos": "93.063.000",
            "Marathonas": "20.000.000",
            "Mornos": "390.000.000",
            "Yliko": "300.000.000",
            "Total": "803.063.000",
        },
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 12))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 4


@pytest.mark.asyncio
async def test_fetch_percentages_derives_correct_pct() -> None:
    """Mornos at 390M m³ / 780M m³ capacity = 0.5"""
    mock_response = httpx.Response(
        200,
        json={
            "Date": "12-03-2026",
            "Eyinos": "65.000.000",
            "Marathonas": "20.500.000",
            "Mornos": "390.000.000",
            "Yliko": "300.000.000",
            "Total": "775.500.000",
        },
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 12))

    mornos = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Mornos")
    assert abs(mornos.percentage - 0.5) < 0.001


@pytest.mark.asyncio
async def test_fetch_percentages_total_is_weighted_average() -> None:
    mock_response = httpx.Response(
        200,
        json={
            "Date": "12-03-2026",
            "Eyinos": "65.000.000",
            "Marathonas": "20.500.000",
            "Mornos": "390.000.000",
            "Yliko": "300.000.000",
            "Total": "775.500.000",
        },
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 12))

    # Total = 775.5M / 1551M total capacity = ~0.5
    total_capacity_mcm = 780 + 600 + 130 + 41  # 1551 MCM
    expected = 775.5 / total_capacity_mcm
    assert abs(result.total_percentage - expected) < 0.001


@pytest.mark.asyncio
async def test_fetch_date_statistics_inflow_is_zero() -> None:
    mock_response = httpx.Response(
        200,
        json={
            "Date": "12-03-2026",
            "Eyinos": "65.000.000",
            "Marathonas": "20.500.000",
            "Mornos": "390.000.000",
            "Yliko": "300.000.000",
            "Total": "775.500.000",
        },
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 12))

    assert isinstance(result, DateStatistics)
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 12))


def test_date_format_is_dd_mm_yyyy() -> None:
    """The EYDAP API expects DD-MM-YYYY format."""
    d = date(2026, 3, 12)
    assert d.strftime("%d-%m-%Y") == "12-03-2026"
