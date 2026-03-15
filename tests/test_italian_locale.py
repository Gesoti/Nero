"""Tests for Italian locale translations."""
from __future__ import annotations

import httpx
import pytest


async def test_italian_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """Italian locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=it", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=it" in cookie


async def test_italian_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=it must change html lang to it."""
    resp = await async_client.get("/", cookies={"wl_lang": "it"})
    assert resp.status_code == 200
    assert 'lang="it"' in resp.text


async def test_italian_nav_translated(async_client: httpx.AsyncClient) -> None:
    """Italian locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "it"})
    assert resp.status_code == 200
    assert "Mappa" in resp.text


async def test_italian_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Italiano must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Italiano" in resp.text
