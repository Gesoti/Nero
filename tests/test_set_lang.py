"""Tests for the /set-lang language switching endpoint and dropdown UI."""
from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.config import settings
from app.db import upsert_dams, upsert_percentage_snapshot
from app.main import app
from tests.conftest import _DamStub, _SnapshotStub


# ── /set-lang endpoint tests ─────────────────────────────────────────────


async def test_set_lang_redirects_with_cookie(async_client: httpx.AsyncClient) -> None:
    """GET /set-lang?lang=el&next=/ must redirect and set wl_lang cookie."""
    resp = await async_client.get("/set-lang?lang=el&next=/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
    cookie_header = resp.headers.get("set-cookie", "")
    assert "wl_lang=el" in cookie_header


async def test_set_lang_defaults_to_english(async_client: httpx.AsyncClient) -> None:
    """GET /set-lang without params must default to English."""
    resp = await async_client.get("/set-lang", follow_redirects=False)
    assert resp.status_code == 302
    cookie_header = resp.headers.get("set-cookie", "")
    assert "wl_lang=en" in cookie_header


async def test_set_lang_rejects_invalid_locale(async_client: httpx.AsyncClient) -> None:
    """Invalid lang values must fall back to English."""
    resp = await async_client.get("/set-lang?lang=xx&next=/", follow_redirects=False)
    assert resp.status_code == 302
    cookie_header = resp.headers.get("set-cookie", "")
    assert "wl_lang=en" in cookie_header


async def test_set_lang_prevents_open_redirect(async_client: httpx.AsyncClient) -> None:
    """next parameter must be a relative path — absolute URLs are blocked."""
    resp = await async_client.get(
        "/set-lang?lang=en&next=https://evil.com", follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


# ── Language dropdown in navbar ──────────────────────────────────────────


async def test_language_dropdown_present(async_client: httpx.AsyncClient) -> None:
    """The language dropdown toggle must be present in the navbar."""
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert 'id="lang-toggle"' in resp.text
    assert 'id="lang-dropdown"' in resp.text


async def test_language_dropdown_has_greek_option(async_client: httpx.AsyncClient) -> None:
    """The language dropdown must include Greek as an option."""
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert "Ελληνικά" in resp.text


# ── Greek rendering via cookie ───────────────────────────────────────────


async def test_greek_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=el cookie must change html lang attribute."""
    resp = await async_client.get("/", cookies={"wl_lang": "el"})
    assert resp.status_code == 200
    assert 'lang="el"' in resp.text


async def test_greek_cookie_translates_nav_strings(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=el must render nav items in Greek."""
    resp = await async_client.get("/", cookies={"wl_lang": "el"})
    assert resp.status_code == 200
    # "Map" → "Χάρτης", "About" → "Σχετικά"
    assert "Χάρτης" in resp.text
    assert "Σχετικά" in resp.text


async def test_english_is_default_without_cookie(async_client: httpx.AsyncClient) -> None:
    """Without a language cookie, pages render in English."""
    resp = await async_client.get("/")
    assert resp.status_code == 200
    assert 'lang="en"' in resp.text
    # English nav strings should appear
    assert ">Map<" in resp.text or "Map</a>" in resp.text
