"""
Tests for the Portugal data provider.
Data source: infoagua.apambiente.pt embedded DATA_SupStations JSON.
"""
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.portugal import (
    PortugalProvider,
    _parse_pt_volume,
    _PORTUGAL_DAMS,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def portugal_provider() -> PortugalProvider:
    client = httpx.AsyncClient(base_url="https://infoagua.apambiente.pt")
    return PortugalProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_portugal_provider_importable() -> None:
    from app.providers.portugal import PortugalProvider
    assert PortugalProvider is not None


def test_portugal_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = PortugalProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_20_reservoirs(portugal_provider: PortugalProvider) -> None:
    dams = await portugal_provider.fetch_dams()
    assert len(dams) == 20


@pytest.mark.asyncio
async def test_fetch_dams_largest_is_alqueva(portugal_provider: PortugalProvider) -> None:
    dams = await portugal_provider.fetch_dams()
    alqueva = next(d for d in dams if d.name_en == "Alqueva")
    assert alqueva.capacity_mcm == 4150.0


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(portugal_provider: PortugalProvider) -> None:
    dams = await portugal_provider.fetch_dams()
    for dam in dams:
        assert dam.lat != 0.0, f"{dam.name_en} has lat=0"
        assert dam.lng != 0.0, f"{dam.name_en} has lng=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_capacity(portugal_provider: PortugalProvider) -> None:
    dams = await portugal_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has capacity=0"
        assert dam.capacity_m3 > 0, f"{dam.name_en} has capacity_m3=0"


@pytest.mark.asyncio
async def test_fetch_dams_all_in_portugal_latitude_range(portugal_provider: PortugalProvider) -> None:
    """All dams should be within mainland Portugal's bounding box."""
    dams = await portugal_provider.fetch_dams()
    for dam in dams:
        assert 36.9 <= dam.lat <= 42.2, f"{dam.name_en} lat {dam.lat} outside Portugal"
        assert -9.5 <= dam.lng <= -6.1, f"{dam.name_en} lng {dam.lng} outside Portugal"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(portugal_provider: PortugalProvider) -> None:
    """name_en must be ASCII-safe for URL paths."""
    dams = await portugal_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


# ── Volume parser tests ──────────────────────────────────────────────────────

def test_parse_pt_volume_decimal_string() -> None:
    assert abs(_parse_pt_volume("4054.512") - 4054.512) < 0.001


def test_parse_pt_volume_integer_string() -> None:
    assert abs(_parse_pt_volume("132") - 132.0) < 0.001


def test_parse_pt_volume_zero() -> None:
    assert _parse_pt_volume("0") == 0.0


def test_parse_pt_volume_with_spaces() -> None:
    assert abs(_parse_pt_volume(" 368.277 ") - 368.277) < 0.001


# ── fetch_percentages tests (mocked HTTP) ────────────────────────────────────

# Mock HTML with embedded DATA_SupStations matching real structure
_MOCK_INFOAGUA_HTML = """
<html><head><script>
var DATA_SupStations = [
  {"id":1,"name":"ALQUEVA","max_volume":4150,"latitude":"38.197","longitude":"-7.495",
   "basin_name":"Guadiana","recent_value":"4054.512","recent_date":"fevereiro 2026",
   "recent_value_percentage":97.7,"usable_volume":3150,"snirh_code":"1627743416"},
  {"id":2,"name":"BAIXO SABOR","max_volume":1095,"latitude":"41.228605","longitude":"-7.012504",
   "basin_name":"Douro","recent_value":"1076.771","recent_date":"fevereiro 2026",
   "recent_value_percentage":98.34,"usable_volume":630,"snirh_code":"7554777518"},
  {"id":3,"name":"CASTELO DE BODE","max_volume":1095,"latitude":"39.545","longitude":"-8.323",
   "basin_name":"Tejo","recent_value":"1061.684","recent_date":"fevereiro 2026",
   "recent_value_percentage":96.96,"usable_volume":902,"snirh_code":"1627743896"},
  {"id":4,"name":"CABRIL","max_volume":720,"latitude":"39.929","longitude":"-8.127",
   "basin_name":"Tejo","recent_value":"649.57","recent_date":"fevereiro 2026",
   "recent_value_percentage":90.22,"usable_volume":615,"snirh_code":"1627743586"},
  {"id":5,"name":"ALTO RABAGÃO","max_volume":568.7,"latitude":"41.732","longitude":"-7.861",
   "basin_name":"Cávado","recent_value":"562.523","recent_date":"fevereiro 2026",
   "recent_value_percentage":98.91,"usable_volume":550,"snirh_code":"1627743430"},
  {"id":6,"name":"ST.A CLARA","max_volume":485,"latitude":"37.516","longitude":"-8.44",
   "basin_name":"Mira","recent_value":"477.10974","recent_date":"fevereiro 2026",
   "recent_value_percentage":98.37,"usable_volume":240.3,"snirh_code":"1627759384"},
  {"id":7,"name":"AGUIEIRA","max_volume":423,"latitude":"40.340723246","longitude":"-8.19670825",
   "basin_name":"Mondego","recent_value":"320.298","recent_date":"fevereiro 2026",
   "recent_value_percentage":75.72,"usable_volume":216,"snirh_code":"1627743384"},
  {"id":8,"name":"ALTO LINDOSO","max_volume":379,"latitude":"41.871","longitude":"-8.205",
   "basin_name":"Lima","recent_value":"368.277","recent_date":"fevereiro 2026",
   "recent_value_percentage":97.17,"usable_volume":347.91,"snirh_code":"1627743428"},
  {"id":9,"name":"MARANHÃO","max_volume":205.4,"latitude":"39.015","longitude":"-7.976",
   "basin_name":"Tejo","recent_value":"195.288","recent_date":"fevereiro 2026",
   "recent_value_percentage":95.08,"usable_volume":180.9,"snirh_code":"1627758764"},
  {"id":10,"name":"CAIA","max_volume":203,"latitude":"38.996","longitude":"-7.14",
   "basin_name":"Guadiana","recent_value":"182.826","recent_date":"fevereiro 2026",
   "recent_value_percentage":90.06,"usable_volume":192.3,"snirh_code":"1627743648"},
  {"id":11,"name":"PARADELA","max_volume":164.4,"latitude":"41.761","longitude":"-7.957",
   "basin_name":"Cávado","recent_value":"161.564","recent_date":"fevereiro 2026",
   "recent_value_percentage":98.27,"usable_volume":158.2,"snirh_code":"1627758928"},
  {"id":12,"name":"MONTARGIL","max_volume":164.3,"latitude":"39.053","longitude":"-8.175",
   "basin_name":"Tejo","recent_value":"164.371","recent_date":"fevereiro 2026",
   "recent_value_percentage":100.04,"usable_volume":142.7,"snirh_code":"1627758816"},
  {"id":13,"name":"CANIÇADA","max_volume":159.3,"latitude":"41.652","longitude":"-8.235",
   "basin_name":"Cávado","recent_value":"143.152","recent_date":"fevereiro 2026",
   "recent_value_percentage":89.86,"usable_volume":144.4,"snirh_code":"1627743674"},
  {"id":14,"name":"ODELOUCA","max_volume":157,"latitude":"37.28694","longitude":"-8.471098",
   "basin_name":"Arade","recent_value":"137.394","recent_date":"fevereiro 2026",
   "recent_value_percentage":87.51,"usable_volume":134,"snirh_code":"3507536920"},
  {"id":15,"name":"CARRAPATELO","max_volume":150.2,"latitude":"41.088","longitude":"-8.126",
   "basin_name":"Douro","recent_value":"135.099","recent_date":"fevereiro 2026",
   "recent_value_percentage":89.95,"usable_volume":15.6,"snirh_code":"1627743682"},
  {"id":16,"name":"RIBEIRADIO","max_volume":136.4,"latitude":"40.742218","longitude":"-8.319449",
   "basin_name":"Vouga","recent_value":"130.297","recent_date":"fevereiro 2026",
   "recent_value_percentage":95.53,"usable_volume":84.6,"snirh_code":"7554777512"},
  {"id":17,"name":"ALVITO","max_volume":132.5,"latitude":"38.275","longitude":"-7.921",
   "basin_name":"Sado","recent_value":"132.5","recent_date":"fevereiro 2026",
   "recent_value_percentage":100,"usable_volume":130,"snirh_code":"1627743440"},
  {"id":18,"name":"ODELEITE","max_volume":130,"latitude":"37.331","longitude":"-7.518",
   "basin_name":"Guadiana","recent_value":"127.28","recent_date":"fevereiro 2026",
   "recent_value_percentage":97.91,"usable_volume":117,"snirh_code":"1627758894"},
  {"id":19,"name":"BEMPOSTA","max_volume":128.8,"latitude":"41.298","longitude":"-6.471",
   "basin_name":"Douro","recent_value":"126.383","recent_date":"fevereiro 2026",
   "recent_value_percentage":98.12,"usable_volume":122.8,"snirh_code":"1627743548"},
  {"id":20,"name":"TORRÃO","max_volume":123.9,"latitude":"41.098","longitude":"-8.262",
   "basin_name":"Douro","recent_value":"95.675","recent_date":"fevereiro 2026",
   "recent_value_percentage":77.22,"usable_volume":40.4,"snirh_code":"1627759468"}
];
</script></head><body></body></html>
"""


@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot() -> None:
    mock_response = httpx.Response(
        200,
        text=_MOCK_INFOAGUA_HTML,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = PortugalProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 20


@pytest.mark.asyncio
async def test_fetch_percentages_alqueva_pct() -> None:
    """Alqueva at 4054.512 hm³ / 4150 hm³ capacity ≈ 0.977"""
    mock_response = httpx.Response(
        200,
        text=_MOCK_INFOAGUA_HTML,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = PortugalProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    alqueva = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Alqueva")
    # 97.7% → 0.977
    assert abs(alqueva.percentage - 0.977) < 0.01


@pytest.mark.asyncio
async def test_fetch_percentages_raises_on_http_error() -> None:
    mock_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = PortugalProvider(client=client)
    with pytest.raises(UpstreamAPIError):
        await provider.fetch_percentages(date(2026, 3, 14))


@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    mock_response = httpx.Response(
        200,
        text=_MOCK_INFOAGUA_HTML,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = PortugalProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 14))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 20
    for stat in result.dam_statistics:
        assert stat.inflow_mcm == 0.0


@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(portugal_provider: PortugalProvider) -> None:
    result = await portugal_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(portugal_provider: PortugalProvider) -> None:
    result = await portugal_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(portugal_provider: PortugalProvider) -> None:
    result = await portugal_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []


@pytest.mark.asyncio
async def test_fetch_percentages_handles_missing_dam_in_upstream() -> None:
    """If upstream data lacks a dam from our hardcoded list, use 0.0 for that dam."""
    # Only include Alqueva in mock data — other 19 are missing
    partial_html = """
    <html><head><script>
    var DATA_SupStations = [
      {"id":1,"name":"ALQUEVA","max_volume":4150,"latitude":"38.197","longitude":"-7.495",
       "basin_name":"Guadiana","recent_value":"4054.512","recent_date":"fevereiro 2026",
       "recent_value_percentage":97.7,"usable_volume":3150,"snirh_code":"1627743416"}
    ];
    </script></head><body></body></html>
    """
    mock_response = httpx.Response(
        200,
        text=partial_html,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = PortugalProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 14))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 20
    # Alqueva should have data
    alqueva = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Alqueva")
    assert alqueva.percentage > 0
    # Others should be 0
    cabril = next(dp for dp in result.dam_percentages if dp.dam_name_en == "Cabril")
    assert cabril.percentage == 0.0
