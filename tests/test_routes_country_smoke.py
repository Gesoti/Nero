"""
Parametrized smoke tests for non-primary country routes.

Covers 10 countries (at, bg, ch, cz, de, fi, it, no, pl, pt) that all share
the same route structure and graceful-degradation behaviour. Each country gets
a fixture-pair (plain + seeded), then a single parametrized test class runs
the same assertions for every country.

gr and es are kept in their own files because they have additional
content-type assertions and specific sitemap dam-URL checks that differ from
this common template.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio

from app.config import settings
from app.db import upsert_dams, upsert_percentage_snapshot
from app.main import app
from app.middleware.country import CountryPrefixMiddleware
from tests.conftest import _DamStub, _SnapshotStub


# ── Per-country metadata ──────────────────────────────────────────────────────

@dataclass
class _CountrySpec:
    """All data that varies per country for smoke testing."""

    cc: str                         # ISO country code / URL prefix
    enabled: str                    # comma-separated enabled_countries patch value
    enabled_list: list[str]         # list form for middleware constructor
    html_lang: str                  # expected lang= attribute on dashboard
    footer_contains: list[str]      # any-of strings for footer attribution
    nav_contains: list[str]         # any-of strings in country nav
    sitemap_dam: Optional[str]      # a known dam URL that must appear in sitemap


_COUNTRY_SPECS: list[_CountrySpec] = [
    _CountrySpec(
        cc="at",
        enabled="cy,gr,es,pt,at",
        enabled_list=["cy", "gr", "es", "pt", "at"],
        html_lang="en",
        footer_contains=["eHYD"],
        nav_contains=["Austria", "AT"],
        sitemap_dam=None,  # static metadata not yet wired into sitemap
    ),
    _CountrySpec(
        cc="bg",
        enabled="cy,gr,es,pt,fi,no,bg",
        enabled_list=["cy", "gr", "es", "pt", "fi", "no", "bg"],
        html_lang="bg",
        footer_contains=["MOEW"],
        nav_contains=["Bulgaria", "BG"],
        sitemap_dam="/bg/dam/Iskar",
    ),
    _CountrySpec(
        cc="ch",
        enabled="cy,ch",
        enabled_list=["cy", "ch"],
        html_lang="de",
        footer_contains=["BFE", "SFOE"],
        nav_contains=["Switzerland", "CH"],
        sitemap_dam="/ch/dam/Wallis",
    ),
    _CountrySpec(
        cc="cz",
        enabled="cy,gr,es,pt,cz",
        enabled_list=["cy", "gr", "es", "pt", "cz"],
        html_lang="en",
        footer_contains=[],          # cz has no footer attribution test yet
        nav_contains=[],             # cz has no nav test yet
        sitemap_dam=None,
    ),
    _CountrySpec(
        cc="de",
        enabled="cy,gr,es,pt,de",
        enabled_list=["cy", "gr", "es", "pt", "de"],
        html_lang="de",
        footer_contains=["Talsperrenleitzentrale", "LTV"],
        nav_contains=["Germany", "DE"],
        sitemap_dam="/de/dam/Bleiloch",
    ),
    _CountrySpec(
        cc="fi",
        enabled="cy,gr,es,pt,fi",
        enabled_list=["cy", "gr", "es", "pt", "fi"],
        html_lang="en",
        footer_contains=["SYKE"],
        nav_contains=["Finland", "FI"],
        sitemap_dam=None,  # sitemap check was a duplicate 200-only assertion
    ),
    _CountrySpec(
        cc="it",
        enabled="cy,gr,es,pt,it",
        enabled_list=["cy", "gr", "es", "pt", "it"],
        html_lang="en",
        footer_contains=["OpenData Sicilia", "opendatasicilia"],
        nav_contains=["Italy", "IT"],
        sitemap_dam=None,  # per-dam URLs require merge-phase wiring
    ),
    _CountrySpec(
        cc="no",
        enabled="cy,gr,es,pt,fi,no",
        enabled_list=["cy", "gr", "es", "pt", "fi", "no"],
        html_lang="nb",
        footer_contains=["NVE"],
        nav_contains=["Norway", "NO"],
        sitemap_dam="/no/dam/NO1-East",
    ),
    _CountrySpec(
        cc="pl",
        enabled="cy,gr,es,pt,pl",
        enabled_list=["cy", "gr", "es", "pt", "pl"],
        html_lang="pl",
        footer_contains=["IMGW"],
        nav_contains=["Poland", "PL"],
        sitemap_dam="/pl/dam/Solina",
    ),
    _CountrySpec(
        cc="pt",
        enabled="cy,gr,es,pt",
        enabled_list=["cy", "gr", "es", "pt"],
        html_lang="en",
        footer_contains=["SNIRH", "APA", "InfoAgua"],
        nav_contains=["Portugal"],
        sitemap_dam="/pt/dam/Alqueva",
    ),
]

# Index specs by cc for fixture lookup
_SPEC_BY_CC: dict[str, _CountrySpec] = {s.cc: s for s in _COUNTRY_SPECS}


# ── Fixture factory helpers ───────────────────────────────────────────────────

def _make_wrapped_app(spec: _CountrySpec) -> httpx.ASGITransport:
    """Build an ASGITransport wrapping the app with the country middleware."""
    wrapped = CountryPrefixMiddleware(
        app=app,
        enabled_countries=spec.enabled_list,
        default_country="cy",
    )
    return httpx.ASGITransport(app=wrapped)


# ── Per-country fixture pairs ─────────────────────────────────────────────────
# Each fixture is a thin wrapper around the shared factory so pytest can inject
# them by name into tests that need a single specific country client.

@pytest_asyncio.fixture
async def at_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["at"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def at_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["at"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def bg_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["bg"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def bg_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["bg"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def ch_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["ch"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def ch_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["ch"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def cz_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["cz"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def cz_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["cz"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def de_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["de"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def de_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["de"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def fi_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["fi"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def fi_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["fi"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def it_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["it"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def it_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["it"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def no_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["no"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def no_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["no"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def pl_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["pl"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def pl_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["pl"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def pt_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    spec = _SPEC_BY_CC["pt"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def pt_seeded_client(in_memory_db) -> AsyncIterator[httpx.AsyncClient]:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    spec = _SPEC_BY_CC["pt"]
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


# ── Parametrized smoke tests ──────────────────────────────────────────────────
# Each test function receives a fresh client built inline via the spec so that
# pytest parametrize can drive it without needing fixture injection per country.
# We build the client directly inside the test using an async context manager.

async def _plain_client(spec: _CountrySpec, db_fixture: None) -> AsyncIterator[httpx.AsyncClient]:
    """Helper: yield a plain (unseeded) client for the given spec."""
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            yield c


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dashboard_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dashboard_html_lang(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert f'lang="{spec.html_lang}"' in resp.text


@pytest.mark.parametrize("spec,route", [
    pytest.param(s, route, id=f"{s.cc}-{route.strip('/')}")
    for s in _COUNTRY_SPECS
    for route in ["map", "blog", "about", "privacy"]
], )
async def test_country_route_returns_200(spec: _CountrySpec, route: str, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/{route}")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_health_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/health")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_robots_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/robots.txt")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_ads_txt_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/ads.txt")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_sitemap_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/sitemap.xml")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dashboard_has_og_meta(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert "og:title" in resp.text


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dashboard_has_description_meta(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert 'name="description"' in resp.text


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dashboard_security_headers(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert "x-frame-options" in resp.headers
    assert "x-content-type-options" in resp.headers


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dam_detail_returns_200(spec: _CountrySpec, in_memory_db: None) -> None:
    upsert_dams([_DamStub()])
    upsert_percentage_snapshot(_SnapshotStub())
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/dam/Kouris")
    assert resp.status_code == 200


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_dam_detail_nonexistent_404(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/dam/NonexistentDam")
    assert resp.status_code == 404


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_country_sitemap_includes_prefix(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/sitemap.xml")
    assert f"/{spec.cc}/" in resp.text


@pytest.mark.parametrize("spec", [s for s in _COUNTRY_SPECS if s.sitemap_dam], ids=[s.cc for s in _COUNTRY_SPECS if s.sitemap_dam])
async def test_country_sitemap_includes_known_dam(spec: _CountrySpec, in_memory_db: None) -> None:
    """Sitemap must include a known static dam URL for countries that have one wired."""
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/sitemap.xml")
    assert spec.sitemap_dam in resp.text


@pytest.mark.parametrize("spec", [s for s in _COUNTRY_SPECS if s.footer_contains], ids=[s.cc for s in _COUNTRY_SPECS if s.footer_contains])
async def test_country_footer_attribution(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert any(token in resp.text for token in spec.footer_contains)


@pytest.mark.parametrize("spec", [s for s in _COUNTRY_SPECS if s.nav_contains], ids=[s.cc for s in _COUNTRY_SPECS if s.nav_contains])
async def test_country_nav_includes_label(spec: _CountrySpec, in_memory_db: None) -> None:
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get(f"/{spec.cc}/")
    assert any(label in resp.text for label in spec.nav_contains)


@pytest.mark.parametrize("spec", _COUNTRY_SPECS, ids=[s.cc for s in _COUNTRY_SPECS])
async def test_cy_routes_still_work(spec: _CountrySpec, in_memory_db: None) -> None:
    """Cyprus default routes must remain accessible when any other country is enabled."""
    with patch.object(settings, "enabled_countries", spec.enabled):
        async with httpx.AsyncClient(transport=_make_wrapped_app(spec), base_url="http://test") as c:
            resp = await c.get("/")
    assert resp.status_code == 200


# ── Bulgaria-specific: og:locale must be bg_BG ───────────────────────────────

async def test_bg_dashboard_has_bg_locale(bg_client: httpx.AsyncClient) -> None:
    resp = await bg_client.get("/bg/")
    assert "bg_BG" in resp.text


# ── Austria-specific: sitemap includes /at/ static routes ────────────────────

async def test_at_sitemap_includes_at_routes(at_client: httpx.AsyncClient) -> None:
    resp = await at_client.get("/sitemap.xml")
    assert "/at/" in resp.text
