"""
Tests for the Czech Republic data provider.
Data sources: 5 Povodí (basin authority) portals — POH, PMO, PLA, PVL, POD.
"""
import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import date
from app.providers.czech import (
    CzechProvider,
    _CZECH_DAMS,
    _parse_objemy_page,
    _parse_pvl_page,
    _parse_pod_page,
    _PORTAL_URLS,
)
from app.providers.base import (
    DataProvider,
    DateStatistics,
    PercentageSnapshot,
    UpstreamAPIError,
)


@pytest.fixture
def czech_provider() -> CzechProvider:
    client = httpx.AsyncClient(base_url="https://sap.poh.cz")
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


# ── HTML fixtures reflecting actual portal structure ──────────────────────────

# POH/PMO/PLA portals: dataMereniGW table, percentage in objemLbl span
_OBJEMY_HTML = """
<html><body>
<table class="dataMereniGW">
  <tr>
    <th>Nadrz</th><th>Celkovy objem (mil. m3)</th><th>Zasobni prostor</th>
    <th>Zasobni prostor %</th><th>Ovladatelny prostor %</th>
  </tr>
  <tr>
    <td><a href="/portal/Nadrze/cz/pc/VD_Nechranice.aspx">VD Nechranice</a></td>
    <td>288,0</td>
    <td>245,6</td>
    <td><span id="ctl00_phContent_GridView1_ctl02_objemLbl">85,3</span></td>
    <td>82,1</td>
  </tr>
  <tr>
    <td><a href="/portal/Nadrze/cz/pc/VD_Flaje.aspx">VD Flaje</a></td>
    <td>23,0</td>
    <td>18,2</td>
    <td><span id="ctl00_phContent_GridView1_ctl03_objemLbl">72,4</span></td>
    <td>69,0</td>
  </tr>
  <tr>
    <td><a href="/portal/Nadrze/cz/pc/VD_Prisecnice.aspx">VD Prisecnice</a></td>
    <td>50,0</td>
    <td>40,1</td>
    <td><span id="ctl00_phContent_GridView1_ctl04_objemLbl">91,0</span></td>
    <td>88,5</td>
  </tr>
  <tr>
    <td><a href="/portal/Nadrze/cz/pc/VD_Stanovice.aspx">VD Stanovice</a></td>
    <td>21,0</td>
    <td>16,3</td>
    <td><span id="ctl00_phContent_GridView1_ctl05_objemLbl">67,8</span></td>
    <td>64,2</td>
  </tr>
</table>
</body></html>
"""

# POH HTML with diacritics in reservoir names (as seen on real portals)
_OBJEMY_HTML_DIACRITICS = """
<html><body>
<table class="dataMereniGW">
  <tr>
    <th>Nadrz</th><th>Objem</th><th>Zasobni</th><th>%</th>
  </tr>
  <tr>
    <td><a href="#">VD Dalesice</a></td>
    <td>127,0</td><td>108,3</td>
    <td><span id="ctl00_GridView1_ctl02_objemLbl">78,2</span></td>
  </tr>
  <tr>
    <td><a href="#">VD Vranov</a></td>
    <td>133,0</td><td>115,0</td>
    <td><span id="ctl00_GridView1_ctl03_objemLbl">63,5</span></td>
  </tr>
  <tr>
    <td><a href="#">VD Nove Mlyny - Dolni nadrz</a></td>
    <td>142,0</td><td>120,0</td>
    <td><span id="ctl00_GridView1_ctl04_objemLbl">55,0</span></td>
  </tr>
</table>
</body></html>
"""

_PMO_HTML = """
<html><body>
<table class="dataMereniGW">
  <tr>
    <th>Nadrz</th><th>Celkovy objem</th><th>Zasobni</th><th>%</th>
  </tr>
  <tr>
    <td><a href="#">VD Dalesice</a></td>
    <td>127,0</td><td>108,3</td>
    <td><span id="ctl00_GridView1_ctl02_objemLbl">78,2</span></td>
  </tr>
  <tr>
    <td><a href="#">VD Vranov</a></td>
    <td>133,0</td><td>115,0</td>
    <td><span id="ctl00_GridView1_ctl03_objemLbl">63,5</span></td>
  </tr>
  <tr>
    <td><a href="#">VD Nove Mlyny - Dolni nadrz</a></td>
    <td>142,0</td><td>120,0</td>
    <td><span id="ctl00_GridView1_ctl04_objemLbl">55,0</span></td>
  </tr>
</table>
</body></html>
"""

_PLA_HTML = """
<html><body>
<table class="dataMereniGW">
  <tr>
    <th>Nadrz</th><th>Celkovy objem</th><th>Zasobni</th><th>%</th>
  </tr>
  <tr>
    <td><a href="#">VD Josefuv Dul</a></td>
    <td>24,0</td><td>19,5</td>
    <td><span id="ctl00_GridView1_ctl02_objemLbl">88,6</span></td>
  </tr>
</table>
</body></html>
"""

# PVL portal: dataMereniGW table, volume in objemLbl span (mil m3, comma decimal)
# Percentage must be computed as volume / capacity_mcm * 100
_PVL_HTML = """
<html><body>
<table class="dataMereniGW">
  <tr>
    <th>Nadrz</th><th>Objem (mil. m3)</th><th>%</th>
  </tr>
  <tr>
    <td><a href="#">VD Orlik</a></td>
    <td><span id="ctl00_GridView1_ctl02_objemLbl">572,8</span></td>
    <td>80,0</td>
  </tr>
  <tr>
    <td><a href="#">VD Lipno</a></td>
    <td><span id="ctl00_GridView1_ctl03_objemLbl">240,0</span></td>
    <td>78,4</td>
  </tr>
  <tr>
    <td><a href="#">VD Slapy</a></td>
    <td><span id="ctl00_GridView1_ctl04_objemLbl">202,5</span></td>
    <td>75,0</td>
  </tr>
  <tr>
    <td><a href="#">VD Svihov</a></td>
    <td><span id="ctl00_GridView1_ctl05_objemLbl">200,25</span></td>
    <td>75,0</td>
  </tr>
</table>
</body></html>
"""

# POD portal: simple HTML tables, one per reservoir, DOT decimal volumes
_POD_HTML = """
<html><body>
<h3>Slezska Harta</h3>
<table>
  <tr><td>Objem vody v nadrzi (mil.m3)</td><td>180.530</td></tr>
  <tr><td>Pritok (m3/s)</td><td>12.4</td></tr>
</table>
<h3>Kruzberk</h3>
<table>
  <tr><td>Objem vody v nadrzi (mil.m3)</td><td>28.700</td></tr>
  <tr><td>Pritok (m3/s)</td><td>3.1</td></tr>
</table>
<h3>Zermanice</h3>
<table>
  <tr><td>Objem vody v nadrzi (mil.m3)</td><td>19.250</td></tr>
  <tr><td>Pritok (m3/s)</td><td>2.5</td></tr>
</table>
</body></html>
"""


# ── Unit tests for parsing functions ─────────────────────────────────────────

def test_parse_objemy_page_extracts_nechranice() -> None:
    """_parse_objemy_page extracts percentage for a named dam."""
    result = _parse_objemy_page(_OBJEMY_HTML, ["Nechranice", "Flaje", "Prisecnice", "Stanovice"])
    assert "Nechranice" in result
    assert abs(result["Nechranice"] - 85.3) < 0.01


def test_parse_objemy_page_extracts_all_four_poh_dams() -> None:
    result = _parse_objemy_page(_OBJEMY_HTML, ["Nechranice", "Flaje", "Prisecnice", "Stanovice"])
    assert len(result) == 4
    assert abs(result["Flaje"] - 72.4) < 0.01
    assert abs(result["Prisecnice"] - 91.0) < 0.01
    assert abs(result["Stanovice"] - 67.8) < 0.01


def test_parse_objemy_page_nove_mlyny_partial_match() -> None:
    """'VD Nove Mlyny - Dolni nadrz' in portal should match dam name_en 'Nove Mlyny'."""
    result = _parse_objemy_page(_PMO_HTML, ["Dalesice", "Vranov", "Nove Mlyny"])
    assert "Nove Mlyny" in result
    assert abs(result["Nove Mlyny"] - 55.0) < 0.01


def test_parse_objemy_page_pmo_all_three_dams() -> None:
    result = _parse_objemy_page(_PMO_HTML, ["Dalesice", "Vranov", "Nove Mlyny"])
    assert "Dalesice" in result
    assert abs(result["Dalesice"] - 78.2) < 0.01
    assert "Vranov" in result
    assert abs(result["Vranov"] - 63.5) < 0.01


def test_parse_objemy_page_pla_josefuv_dul() -> None:
    """'VD Josefuv Dul' in PLA HTML should match dam name_en 'Josefuv Dul'."""
    result = _parse_objemy_page(_PLA_HTML, ["Josefuv Dul"])
    assert "Josefuv Dul" in result
    assert abs(result["Josefuv Dul"] - 88.6) < 0.01


def test_parse_objemy_page_ignores_unknown_dams() -> None:
    """Dams in HTML but not in the requested list should be ignored."""
    result = _parse_objemy_page(_OBJEMY_HTML, ["Nechranice"])
    assert list(result.keys()) == ["Nechranice"]


def test_parse_objemy_page_no_table_returns_empty() -> None:
    result = _parse_objemy_page("<html><body><p>No table here</p></body></html>", ["Nechranice"])
    assert result == {}


def test_parse_pvl_page_computes_orlik_percentage() -> None:
    """_parse_pvl_page computes percentage from volume / capacity."""
    capacity_map = {"Orlik": 716.0, "Lipno": 306.0, "Slapy": 270.0, "Svihov": 267.0}
    result = _parse_pvl_page(_PVL_HTML, capacity_map)
    assert "Orlik" in result
    expected = 572.8 / 716.0 * 100
    assert abs(result["Orlik"] - expected) < 0.1


def test_parse_pvl_page_computes_all_four_dams() -> None:
    capacity_map = {"Orlik": 716.0, "Lipno": 306.0, "Slapy": 270.0, "Svihov": 267.0}
    result = _parse_pvl_page(_PVL_HTML, capacity_map)
    assert len(result) == 4
    expected_lipno = 240.0 / 306.0 * 100
    assert abs(result["Lipno"] - expected_lipno) < 0.1
    expected_slapy = 202.5 / 270.0 * 100
    assert abs(result["Slapy"] - expected_slapy) < 0.1


def test_parse_pvl_page_no_table_returns_empty() -> None:
    result = _parse_pvl_page("<html><body></body></html>", {"Orlik": 716.0})
    assert result == {}


def test_parse_pod_page_extracts_slezska_harta() -> None:
    """_parse_pod_page extracts volume and computes percentage for Slezska Harta."""
    capacity_map = {"Slezska Harta": 209.0, "Kruzberk": 35.0, "Zermanice": 25.0}
    result = _parse_pod_page(_POD_HTML, capacity_map)
    assert "Slezska Harta" in result
    expected = 180.530 / 209.0 * 100
    assert abs(result["Slezska Harta"] - expected) < 0.1


def test_parse_pod_page_extracts_all_three_dams() -> None:
    capacity_map = {"Slezska Harta": 209.0, "Kruzberk": 35.0, "Zermanice": 25.0}
    result = _parse_pod_page(_POD_HTML, capacity_map)
    assert len(result) == 3
    expected_kruzberk = 28.700 / 35.0 * 100
    assert abs(result["Kruzberk"] - expected_kruzberk) < 0.1
    expected_zermanice = 19.250 / 25.0 * 100
    assert abs(result["Zermanice"] - expected_zermanice) < 0.1


def test_parse_pod_page_no_headers_returns_empty() -> None:
    result = _parse_pod_page("<html><body><p>nothing</p></body></html>", {"Slezska Harta": 209.0})
    assert result == {}


def test_portal_urls_dict_has_five_entries() -> None:
    """_PORTAL_URLS must map each of the 5 basin authority portal URLs."""
    assert len(_PORTAL_URLS) == 5


# ── Integration tests: fetch_percentages with mocked HTTP responses ───────────

def _make_response(url: str, body: str) -> httpx.Response:
    return httpx.Response(200, text=body, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_fetch_percentages_returns_nonzero_with_real_html() -> None:
    """fetch_percentages returns non-zero percentages when portals return valid HTML."""
    url_to_html: dict[str, str] = {
        "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": _OBJEMY_HTML,
        "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": _PMO_HTML,
        "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": _PLA_HTML,
        "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": _PVL_HTML,
        "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": _POD_HTML,
    }

    async def mock_get(url: str, **kwargs: object) -> httpx.Response:
        return _make_response(url, url_to_html[url])

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=mock_get)
    client.is_closed = False

    provider = CzechProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 15))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15

    # Spot-check that parsed dams have non-zero percentages
    pct_by_name = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    assert pct_by_name["Nechranice"] > 0.0
    assert pct_by_name["Orlik"] > 0.0
    assert pct_by_name["Slezska Harta"] > 0.0
    assert pct_by_name["Josefuv Dul"] > 0.0
    assert pct_by_name["Nove Mlyny"] > 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_falls_back_on_portal_error() -> None:
    """If a portal returns HTTP 500, affected dams get 0.0 but others succeed."""
    url_to_html: dict[str, str | None] = {
        "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": _OBJEMY_HTML,
        "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": _PMO_HTML,
        "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": _PLA_HTML,
        # PVL fails
        "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": None,
        "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": _POD_HTML,
    }

    async def mock_get(url: str, **kwargs: object) -> httpx.Response:
        body = url_to_html[url]
        if body is None:
            return httpx.Response(500, request=httpx.Request("GET", url))
        return _make_response(url, body)

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=mock_get)
    client.is_closed = False

    provider = CzechProvider(client=client)
    # Must not raise — graceful degradation
    result = await provider.fetch_percentages(date(2026, 3, 15))

    assert isinstance(result, PercentageSnapshot)
    assert len(result.dam_percentages) == 15
    pct_by_name = {dp.dam_name_en: dp.percentage for dp in result.dam_percentages}
    # POH-sourced dams should still be non-zero
    assert pct_by_name["Nechranice"] > 0.0
    # PVL-sourced dams should fall back to 0.0
    assert pct_by_name["Orlik"] == 0.0


@pytest.mark.asyncio
async def test_fetch_percentages_total_is_nonzero_when_data_present() -> None:
    """total_percentage is > 0 when at least some portals return valid data."""
    url_to_html: dict[str, str] = {
        "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": _OBJEMY_HTML,
        "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": _PMO_HTML,
        "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": _PLA_HTML,
        "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": _PVL_HTML,
        "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": _POD_HTML,
    }

    async def mock_get(url: str, **kwargs: object) -> httpx.Response:
        return _make_response(url, url_to_html[url])

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=mock_get)
    client.is_closed = False

    provider = CzechProvider(client=client)
    result = await provider.fetch_percentages(date(2026, 3, 15))

    assert 0.0 < result.total_percentage <= 100.0


@pytest.mark.asyncio
async def test_fetch_date_statistics_returns_stats() -> None:
    """fetch_date_statistics returns DateStatistics with 15 dams."""
    url_to_html: dict[str, str] = {
        "https://sap.poh.cz/portal/Nadrze/cz/pc/Objemy.aspx": _OBJEMY_HTML,
        "https://sap.pmo.cz/portal/Nadrze/cz/pc/Objemy.aspx": _PMO_HTML,
        "https://www5.pla.cz/portal/nadrze/cz/pc/Objemy.aspx": _PLA_HTML,
        "https://www.pvl.cz/portal/Nadrze/cz/pc/Prehled.aspx": _PVL_HTML,
        "https://www.pod.cz/stranka/stavy-a-prutoky-v-nadrzich-tabulka.html": _POD_HTML,
    }

    async def mock_get(url: str, **kwargs: object) -> httpx.Response:
        return _make_response(url, url_to_html[url])

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=mock_get)
    client.is_closed = False

    provider = CzechProvider(client=client)
    result = await provider.fetch_date_statistics(date(2026, 3, 15))

    assert isinstance(result, DateStatistics)
    assert len(result.dam_statistics) == 15
    for stat in result.dam_statistics:
        # Inflow is always 0.0 — Czech portals don't expose it
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
