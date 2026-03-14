"""Tests for Spanish locale translations."""
from __future__ import annotations

import httpx
import pytest


async def test_spanish_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """Spanish locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=es", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=es" in cookie


async def test_spanish_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=es must change html lang to es."""
    resp = await async_client.get("/", cookies={"wl_lang": "es"})
    assert resp.status_code == 200
    assert 'lang="es"' in resp.text


async def test_spanish_nav_translated(async_client: httpx.AsyncClient) -> None:
    """Spanish locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "es"})
    assert resp.status_code == 200
    assert "Mapa" in resp.text
    assert "Acerca de" in resp.text


async def test_spanish_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Español must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Español" in resp.text
