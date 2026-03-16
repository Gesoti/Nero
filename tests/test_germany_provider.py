"""
Tests for the Germany data provider.
Data sources: Talsperrenleitzentrale Ruhr (9 dams), Sachsen LTV (48 dams).
Ruhr dams are parsed from HTML; Saxony and other dams remain 0.0 until their
parsers are implemented.
"""
from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from datetime import date

from app.providers.germany import (
    GermanyProvider,
    _GERMANY_DAMS,
    _parse_ruhr_page,
    _RUHR_URL,
)
from app.providers.base import (
    DataProvider,
    DamInfo,
    DateStatistics,
    PercentageSnapshot,
)

# ── Minimal Ruhr portal HTML fixture ─────────────────────────────────────────
# Mirrors the actual structure of https://www.talsperrenleitzentrale-ruhr.de/online-daten/talsperren
# Container: <div id="dam-coordinates">; dam cards use `title` attribute for name;
# volume is in text node: "Stauinhalt: 162.01 Mio.m³"

_RUHR_HTML_FIXTURE = """
<html><body>
<div id="dam-coordinates" class="hidden">
    <div data-lon="7.887853" data-lat="51.111176"
         title="Biggetalsperre" id="dam-popover-bigge">
        Stauh&ouml;he: 306.07 m. &uuml;. NHN<br/>
        <small>16.03.2026 um 06:00 Uhr</small><br/>
        Stauinhalt: 162.01 Mio.m&#179;<br/>
        <small>16.03.2026 um 06:00 Uhr</small><br/>
    </div>
    <div data-lon="7.409321" data-lat="51.241241"
         title="Ennepetalsperre" id="dam-popover-ennepe">
        Stauh&ouml;he: 305.7 m. &uuml;. NHN<br/>
        <small>16.03.2026 um 06:15 Uhr</small><br/>
        Stauinhalt: 10.92 Mio.m&#179;<br/>
        <small>16.03.2026 um 06:15 Uhr</small><br/>
    </div>
    <div data-lon="8.059335" data-lat="51.489704"
         title="M&#246;hnetalsperre" id="dam-popover-moehne">
        Stauh&ouml;he: 211.01 m. &uuml;. NHN<br/>
        <small>16.03.2026 um 06:15 Uhr</small><br/>
        Stauinhalt: 109.93 Mio.m&#179;<br/>
        <small>16.03.2026 um 06:00 Uhr</small><br/>
    </div>
    <div data-lon="7.968285" data-lat="51.350979"
         title="Sorpetalsperre" id="dam-popover-sorpe">
        Stauh&ouml;he: 280.26 m. &uuml;. NHN<br/>
        <small>16.03.2026 um 06:15 Uhr</small><br/>
        Stauinhalt: 61.785 Mio.m&#179;<br/>
        <small>16.03.2026 um 06:15 Uhr</small><br/>
    </div>
    <div data-lon="7.685332" data-lat="51.193043"
         title="Versetalsperre" id="dam-popover-verse">
        Stauh&ouml;he: 384.56 m. &uuml;. NHN<br/>
        <small>16.03.2026 um 06:00 Uhr</small><br/>
        Stauinhalt: 24.231 Mio.m&#179;<br/>
        <small>16.03.2026 um 06:00 Uhr</small><br/>
    </div>
</div>
</body></html>
"""


@pytest.fixture
def germany_provider() -> GermanyProvider:
    client = httpx.AsyncClient(base_url="https://www.talsperrenleitzentrale-ruhr.de")
    return GermanyProvider(client=client)


# ── Import & protocol tests ──────────────────────────────────────────────────

def test_germany_provider_importable() -> None:
    from app.providers.germany import GermanyProvider
    assert GermanyProvider is not None


def test_germany_provider_implements_protocol() -> None:
    client = httpx.AsyncClient(base_url="https://example.com")
    provider = GermanyProvider(client=client)
    assert isinstance(provider, DataProvider)


# ── Static metadata tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_dams_returns_15(germany_provider: GermanyProvider) -> None:
    """Germany MVP has 15 hardcoded reservoir entries."""
    dams = await germany_provider.fetch_dams()
    assert len(dams) == 15


@pytest.mark.asyncio
async def test_fetch_dams_all_have_coordinates(germany_provider: GermanyProvider) -> None:
    """All dams must have coordinates within Germany's bounding box."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        # Germany bounding box: lat 47–55, lng 6–15
        assert 47.0 <= dam.lat <= 55.5, f"{dam.name_en} lat {dam.lat} outside Germany"
        assert 6.0 <= dam.lng <= 15.5, f"{dam.name_en} lng {dam.lng} outside Germany"


@pytest.mark.asyncio
async def test_fetch_dams_name_en_is_ascii(germany_provider: GermanyProvider) -> None:
    """name_en must be ASCII-safe for URL path use."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        assert dam.name_en.isascii(), f"{dam.name_en} contains non-ASCII characters"


@pytest.mark.asyncio
async def test_fetch_dams_all_have_positive_capacity(germany_provider: GermanyProvider) -> None:
    """All dams must have a positive capacity in MCM."""
    dams = await germany_provider.fetch_dams()
    for dam in dams:
        assert dam.capacity_mcm > 0, f"{dam.name_en} has zero capacity"


@pytest.mark.asyncio
async def test_fetch_dams_expected_names_present(germany_provider: GermanyProvider) -> None:
    """Verify key reservoir name_en values are present."""
    dams = await germany_provider.fetch_dams()
    names = {d.name_en for d in dams}
    expected_subset = {"Bleiloch", "Edersee", "Bigge", "Mohne", "Hohenwarte"}
    assert expected_subset.issubset(names), f"Missing: {expected_subset - names}"


@pytest.mark.asyncio
async def test_fetch_dams_bleiloch_is_largest(germany_provider: GermanyProvider) -> None:
    """Bleiloch (215 MCM) should be the largest reservoir in the list."""
    dams = await germany_provider.fetch_dams()
    max_dam = max(dams, key=lambda d: d.capacity_mcm)
    assert max_dam.name_en == "Bleiloch"


# ── fetch_percentages stub tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_snapshot(germany_provider: GermanyProvider) -> None:
    """Stub returns a valid PercentageSnapshot with 15 entries."""
    result = await germany_provider.fetch_percentages(date(2026, 3, 16))
    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15


@pytest.mark.asyncio
async def test_fetch_percentages_non_ruhr_dams_are_zero(germany_provider: GermanyProvider) -> None:
    """Non-Ruhr dams (Saxony, Harz etc.) remain 0.0 — no parser implemented yet."""
    result = await germany_provider.fetch_percentages(date(2026, 3, 16))
    non_ruhr = {"Bleiloch", "Edersee", "Hohenwarte", "Rappbode",
                "Grosse-Dhuenn", "Eibenstock", "Poehl", "Kriebstein",
                "Leibis-Lichte", "Agger", "Oker"}
    for dp in result.dam_percentages:
        if dp.dam_name_en in non_ruhr:
            assert dp.percentage == 0.0, (
                f"{dp.dam_name_en} should be 0.0 (no parser)"
            )


@pytest.mark.asyncio
async def test_fetch_percentages_date_matches_target(germany_provider: GermanyProvider) -> None:
    """Snapshot date must match the requested target date."""
    target = date(2026, 3, 16)
    result = await germany_provider.fetch_percentages(target)
    assert result.date == target


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_network_error() -> None:
    """On network error, stub still returns zero-fill defaults (does not raise)."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=httpx.RequestError("connection refused"))
    client.is_closed = False

    provider = GermanyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


# ── _parse_ruhr_page unit tests ───────────────────────────────────────────────

def test_parse_ruhr_page_returns_dict() -> None:
    """_parse_ruhr_page must return a dict mapping name_en → percentage (0-1)."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert isinstance(result, dict)


def test_parse_ruhr_page_extracts_bigge_volume() -> None:
    """Biggetalsperre: 162.01 MCM / 171.7 MCM capacity ≈ 0.9436."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert "Bigge" in result
    expected = 162.01 / 171.7
    assert abs(result["Bigge"] - expected) < 1e-4, (
        f"Bigge percentage {result['Bigge']:.4f} != expected {expected:.4f}"
    )


def test_parse_ruhr_page_extracts_mohne_volume() -> None:
    """Möhnetalsperre: 109.93 MCM / 134.5 MCM ≈ 0.8175."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert "Mohne" in result
    expected = 109.93 / 134.5
    assert abs(result["Mohne"] - expected) < 1e-4


def test_parse_ruhr_page_extracts_sorpe_volume() -> None:
    """Sorpetalsperre: 61.785 MCM / 70.4 MCM ≈ 0.8777."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert "Sorpe" in result
    expected = 61.785 / 70.4
    assert abs(result["Sorpe"] - expected) < 1e-4


def test_parse_ruhr_page_extracts_verse_volume() -> None:
    """Versetalsperre: 24.231 MCM / 32.8 MCM ≈ 0.7387."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert "Verse" in result
    expected = 24.231 / 32.8
    assert abs(result["Verse"] - expected) < 1e-4


def test_parse_ruhr_page_ignores_unknown_dam_names() -> None:
    """Ennepetalsperre is not in _GERMANY_DAMS — must not appear in result."""
    result = _parse_ruhr_page(_RUHR_HTML_FIXTURE)
    assert "Ennepe" not in result


def test_parse_ruhr_page_clamps_percentage_to_one() -> None:
    """Percentage must not exceed 1.0 even if live volume exceeds capacity (sensor error)."""
    html = """
    <div id="dam-coordinates">
      <div title="Biggetalsperre" id="dam-popover-bigge">
        Stauinhalt: 999.99 Mio.m³<br/>
      </div>
    </div>
    """
    result = _parse_ruhr_page(html)
    assert result.get("Bigge", 1.0) <= 1.0


def test_parse_ruhr_page_returns_empty_on_malformed_html() -> None:
    """Malformed / empty HTML must return empty dict, not raise."""
    result = _parse_ruhr_page("<html><body>no dam data here</body></html>")
    assert result == {}


def test_parse_ruhr_page_handles_missing_volume_gracefully() -> None:
    """A card without a Stauinhalt line must be skipped, not crash."""
    html = """
    <div id="dam-coordinates">
      <div title="Biggetalsperre" id="dam-popover-bigge">
        Stauh&ouml;he: 306.07 m. &uuml;. NHN<br/>
      </div>
    </div>
    """
    result = _parse_ruhr_page(html)
    # Bigge card has no volume — should be absent from result, not raise
    assert "Bigge" not in result


# ── fetch_percentages with mocked HTTP ───────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_percentages_returns_nonzero_for_ruhr_dams() -> None:
    """With a valid Ruhr HTML response, Bigge/Mohne/Sorpe/Verse must be > 0."""
    mock_response = MagicMock()
    mock_response.text = _RUHR_HTML_FIXTURE
    mock_response.raise_for_status = MagicMock()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GermanyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))

    ruhr_dams = {"Bigge", "Mohne", "Sorpe", "Verse"}
    found = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    for name in ruhr_dams:
        assert found[name] > 0.0, f"{name} should have non-zero percentage from Ruhr parse"


@pytest.mark.asyncio
async def test_fetch_percentages_ruhr_dams_capped_at_one() -> None:
    """Ruhr dam percentages must never exceed 1.0."""
    mock_response = MagicMock()
    mock_response.text = _RUHR_HTML_FIXTURE
    mock_response.raise_for_status = MagicMock()

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GermanyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))
    for dp in result.dam_percentages:
        assert dp.percentage <= 1.0, f"{dp.dam_name_en} percentage {dp.percentage} > 1.0"


@pytest.mark.asyncio
async def test_fetch_percentages_graceful_on_http_error() -> None:
    """HTTP error (4xx/5xx) must not raise — fall back to zero-fill."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "503", request=MagicMock(), response=MagicMock()
    ))

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.is_closed = False

    provider = GermanyProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 16))
    assert isinstance(result, PercentageSnapshot)
    assert all(dp.percentage == 0.0 for dp in result.dam_percentages)


# ── fetch_date_statistics stub tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_15_entries(germany_provider: GermanyProvider) -> None:
    """fetch_date_statistics must return stats for all 15 dams."""
    result = await germany_provider.fetch_date_statistics(date(2026, 3, 16))
    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15


@pytest.mark.asyncio
async def test_fetch_date_statistics_all_zero(germany_provider: GermanyProvider) -> None:
    """Stub returns 0.0 storage for all dams."""
    result = await germany_provider.fetch_date_statistics(date(2026, 3, 16))
    for stat in result.dam_statistics:
        assert stat.storage_mcm == 0.0


# ── Stub method tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_timeseries_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_timeseries()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_monthly_inflows_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_monthly_inflows()
    assert result == []


@pytest.mark.asyncio
async def test_fetch_events_returns_empty(germany_provider: GermanyProvider) -> None:
    result = await germany_provider.fetch_events(date(2020, 1, 1), date(2026, 1, 1))
    assert result == []
