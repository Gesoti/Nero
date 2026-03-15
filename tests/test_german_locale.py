"""Tests for German locale translations (used for Austria)."""
from __future__ import annotations

import httpx
import pytest


async def test_german_locale_in_supported(async_client: httpx.AsyncClient) -> None:
    """German locale must be accepted by /set-lang."""
    resp = await async_client.get("/set-lang?lang=de", follow_redirects=False)
    assert resp.status_code == 302
    cookie = resp.headers.get("set-cookie", "")
    assert "wl_lang=de" in cookie


async def test_german_cookie_changes_html_lang(async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang=de must change html lang to de."""
    resp = await async_client.get("/", cookies={"wl_lang": "de"})
    assert resp.status_code == 200
    assert 'lang="de"' in resp.text


async def test_german_nav_translated(async_client: httpx.AsyncClient) -> None:
    """German locale should translate nav items."""
    resp = await async_client.get("/", cookies={"wl_lang": "de"})
    assert resp.status_code == 200
    assert "Karte" in resp.text


async def test_german_language_label_in_dropdown(async_client: httpx.AsyncClient) -> None:
    """Deutsch must appear in the language dropdown."""
    resp = await async_client.get("/")
    assert "Deutsch" in resp.text
