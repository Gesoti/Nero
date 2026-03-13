import pytest
import pytest_asyncio
import httpx
from app.providers.greece import GreeceProvider
from app.providers.base import DataProvider


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
    from datetime import date
    result = await greece_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
