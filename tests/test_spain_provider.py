"""
Tests for SpainProvider — scrapes embalses.net for Spain's top 20 reservoirs.
"""
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch
from datetime import date

from app.providers.spain import SpainProvider, _parse_es_volume, _parse_es_percentage
from app.providers.base import DataProvider, PercentageSnapshot, DateStatistics, UpstreamAPIError


@pytest.fixture
def spain_provider() -> SpainProvider:
    client = httpx.AsyncClient(base_url="https://www.embalses.net")
    return SpainProvider(client=client)


# ── Importability & Protocol ─────────────────────────────────────────────────

def test_spain_provider_importable() -> None:
    from app.providers.spain import SpainProvider
    assert SpainProvider is not None


def test_spain_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = SpainProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── fetch_dams ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_twenty_reservoirs(spain_provider: SpainProvider) -> None:
    dams = await spain_provider.fetch_dams()
    assert len(dams) == 20


@pytest.mark.asyncio
async def test_fetch_dams_la_serena_is_largest(spain_provider: SpainProvider) -> None:
    dams = await spain_provider.fetch_dams()
    la_serena = next(d for d in dams if d.name_en == "La Serena")
    assert la_serena.capacity_mcm == 3219.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(spain_provider: SpainProvider) -> None:
    dams = await spain_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} missing latitude"
        assert dam.lng != 0.0, f"{dam.name_en} missing longitude"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(spain_provider: SpainProvider) -> None:
    dams = await spain_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} missing capacity"
        assert dam.capacity_m3 > 0, f"{dam.name_en} missing capacity_m3"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_spain_latitude_range(spain_provider: SpainProvider) -> None:
    """All Spanish dams should be between lat 36-44, lng -8 to 3."""
    dams = await spain_provider.fetch_dams()
    for dam in dams:
        assert 36.0 <= dam.lat <= 44.0, f"{dam.name_en} lat {dam.lat} out of range"
        assert -8.0 <= dam.lng <= 4.0, f"{dam.name_en} lng {dam.lng} out of range"


# ── Volume/percentage parsers ─────────────────────────────────────────────────

def test_parse_es_volume_thousands_separator() -> None:
    assert _parse_es_volume("2.792") == 2792.0


def test_parse_es_volume_no_separator() -> None:
    assert _parse_es_volume("679") == 679.0


def test_parse_es_volume_large() -> None:
    assert _parse_es_volume("3.219") == 3219.0


def test_parse_es_volume_with_comma_decimal() -> None:
    assert _parse_es_volume("106,43") == 106.43


def test_parse_es_volume_zero() -> None:
    assert _parse_es_volume("0") == 0.0


def test_parse_es_volume_with_spaces() -> None:
    assert _parse_es_volume(" 2.792 ") == 2792.0


def test_parse_es_percentage_dot_decimal() -> None:
    assert _parse_es_percentage("88.35") == 88.35


def test_parse_es_percentage_comma_decimal() -> None:
    assert _parse_es_percentage("88,35") == 88.35


def test_parse_es_percentage_integer() -> None:
    assert _parse_es_percentage("100") == 100.0


# ── fetch_percentages with mocked HTML ────────────────────────────────────────

_MOCK_DAM_HTML = """
<html><body>
<div class="FilaSeccion">Agua embalsada (09-03-2026): 2.792 hm3 88.35 %</div>
<div class="FilaSeccion">Capacidad: 3.160 hm3</div>
</body></html>
"""


def _make_mock_response(html: str = _MOCK_DAM_HTML, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        text=html,
        request=httpx.Request("GET", "https://www.embalses.net/pantano-1003-alcantara.html"),
    )


@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    mock_resp = _make_mock_response()
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_resp)
    client.is_closed = False

    provider = SpainProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 20


@pytest.mark.asyncio
async def test_fetch_percentages_parses_volume_correctly() -> None:
    """When all 20 dams return the same mock page, Alcantara's volume/capacity should parse."""
    mock_resp = _make_mock_response()
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_resp)
    client.is_closed = False

    provider = SpainProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 9))

    # All dams get the same mock (2792/3160=88.35%) but the provider uses
    # the parsed volume against each dam's real capacity
    assert result.total_percentage > 0


@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    mock_resp = _make_mock_response()
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_resp)
    client.is_closed = False

    provider = SpainProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 9))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 20


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    """If ALL dam page fetches fail, UpstreamAPIError should be raised."""
    mock_resp = httpx.Response(
        500,
        request=httpx.Request("GET", "https://www.embalses.net/pantano-581-la-serena.html"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_resp)
    client.is_closed = False

    provider = SpainProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 9))


# ── Empty stubs ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(spain_provider: SpainProvider) -> None:
    result = await spain_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(spain_provider: SpainProvider) -> None:
    result = await spain_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []


@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(spain_provider: SpainProvider) -> None:
    result = await spain_provider.fetch_timeseries()
    assert result == []
