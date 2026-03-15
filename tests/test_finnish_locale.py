"""Tests for Finnish locale translations."""
from __future__ import annotations

import httpx
import pytest


async def test_finnish_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """Finnish locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=fi", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=fi" in cookie


async def test_finnish_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=fi must change html lang to fi."""
    resp = await async_client.get("/", cookies={"wl_lang": "fi"})
    assert resp.status_code == 200
    assert 'lang="fi"' in resp.text


async def test_finnish_nav_translated(async_client: httpx.AsyncClient) -> None:
    """Finnish locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "fi"})
    assert resp.status_code == 200
    assert "Kartta" in resp.text


async def test_finnish_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Suomi must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Suomi" in resp.text
