"""Tests for Norwegian Bokmål locale translations."""
from __future__ import annotations

import httpx
import pytest


async def test_norwegian_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """Norwegian locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=nb", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=nb" in cookie


async def test_norwegian_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=nb must change html lang to nb."""
    resp = await async_client.get("/", cookies={"wl_lang": "nb"})
    assert resp.status_code == 200
    assert 'lang="nb"' in resp.text


async def test_norwegian_nav_translated(async_client: httpx.AsyncClient) -> None:
    """Norwegian locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "nb"})
    assert resp.status_code == 200
    assert "Kart" in resp.text


async def test_norwegian_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Norsk must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Norsk" in resp.text
