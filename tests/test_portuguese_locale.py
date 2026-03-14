"""Tests for Portuguese locale translations."""
from __future__ import annotations

import httpx
import pytest


async def test_portuguese_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """Portuguese locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=pt", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=pt" in cookie


async def test_portuguese_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=pt must change html lang to pt."""
    resp = await async_client.get("/", cookies={"wl_lang": "pt"})
    assert resp.status_code == 200
    assert 'lang="pt"' in resp.text


async def test_portuguese_nav_translated(async_client: httpx.AsyncClient) -> None:
    """Portuguese locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "pt"})
    assert resp.status_code == 200
    assert "Mapa" in resp.text
    assert "Sobre" in resp.text


async def test_portuguese_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Português must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Português" in resp.text
