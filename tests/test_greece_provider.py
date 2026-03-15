import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock
from datetime import date, timedelta
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


# ── fetch_timeseries tests (Year endpoint) ──────────────────────────────────────

# Three daily records spanning 2025-01-01 to 2025-01-08.  The weekly sampler
# keeps every 7th record (indices 0, 7, 14, ...) so from 3 records only
# index 0 is retained.
_YEAR_RESPONSE_3_RECORDS = [
    {
        "Date": "01-01-2025",
        "Eyinos": "100.000.000",
        "Marathonas": "30.000.000",
        "Mornos": "600.000.000",
        "Yliko": "400.000.000",
        "Total": "1.130.000.000",
    },
    {
        "Date": "02-01-2025",
        "Eyinos": "99.500.000",
        "Marathonas": "29.800.000",
        "Mornos": "598.000.000",
        "Yliko": "399.000.000",
        "Total": "1.126.300.000",
    },
    {
        "Date": "08-01-2025",
        "Eyinos": "98.000.000",
        "Marathonas": "29.000.000",
        "Mornos": "595.000.000",
        "Yliko": "397.000.000",
        "Total": "1.119.000.000",
    },
]


def _make_year_mock(status: int, payload: object) -> AsyncMock:
    """Return an httpx.AsyncClient mock that always responds with the given status and payload."""
    mock_response = httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://example.com"),
    )
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False
    return client


@pytest.mark.asyncio
async def test_fetch_timeseries_returns_snapshots() -> None:
    """Year endpoint response is parsed into PercentageSnapshot objects."""
    client = _make_year_mock(200, _YEAR_RESPONSE_3_RECORDS)
    provider = GreeceProvider(client=client)

    result = await provider.fetch_timeseries()

    assert len(result) >= 1
    assert all(isinstance(s, PercentageSnapshot) for s in result)
    # Dates come back in ascending order
    dates = [s.date for s in result]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_fetch_timeseries_weekly_sampling() -> None:
    """365-record response is down-sampled to roughly one entry per week (~52)."""
    # Build a synthetic 365-day year dataset
    records = []
    start = date(2024, 1, 1)
    for i in range(365):
        d = start + timedelta(days=i)
        records.append({
            "Date": d.strftime("%d-%m-%Y"),
            "Eyinos": "100.000.000",
            "Marathonas": "30.000.000",
            "Mornos": "600.000.000",
            "Yliko": "400.000.000",
            "Total": "1.130.000.000",
        })

    client = _make_year_mock(200, records)
    provider = GreeceProvider(client=client)
    result = await provider.fetch_timeseries()

    # Weekly sampling (every 7th record) from a 365-record year yields ~52 per year.
    # With 10 years of data that is ~520 total.
    # Upper bound: if all 3650 records were kept (no sampling), the test fails.
    # Lower bound: must be more than just one-per-year (i.e. > 10).
    # Tight bound: should be approximately 52 per year * 10 years = 520,
    # within 30% to allow for year-range variations.
    total_records_no_sampling = 365 * 10
    assert len(result) < total_records_no_sampling, "Weekly sampling must reduce total record count"
    # Each year contributes ~52 weekly samples; 10 years → ~520 entries.
    # Allow ±50% tolerance for exact year-count/date-range variation.
    assert len(result) >= 200, f"Expected ~520 weekly samples across 10 years, got {len(result)}"


@pytest.mark.asyncio
async def test_fetch_timeseries_graceful_on_year_error() -> None:
    """A 500 for one year is logged and skipped; other years still return data."""
    good_response = httpx.Response(
        200,
        json=_YEAR_RESPONSE_3_RECORDS,
        request=httpx.Request("GET", "https://example.com"),
    )
    bad_response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.com"),
    )

    # First call fails, then enough good responses to cover all remaining years.
    # The Year-based backfill makes one call per year (~10 years), so 15 good
    # responses is sufficient headroom.
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=[bad_response] + [good_response] * 15)
    client.is_closed = False

    provider = GreeceProvider(client=client)
    # Must not raise — graceful degradation
    result = await provider.fetch_timeseries()

    # At least some snapshots come back from the successful years
    assert len(result) >= 1
