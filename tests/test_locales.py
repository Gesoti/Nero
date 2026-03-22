"""
Parametrized locale tests for all non-default UI languages.

Each locale must:
1. Be accepted by /set-lang (302 + cookie).
2. Change html lang= when the cookie is set.
3. Translate at least one nav item.
4. Show its display label in the language dropdown.

The ``nav_word`` value is the translated "Map" nav item (or equivalent
distinctive word) that confirms the locale's .mo file is loaded.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest


@dataclass
class _LocaleSpec:
    code: str           # BCP-47 locale code used in cookie / /set-lang
    label: str          # Display name shown in the language dropdown
    nav_word: str       # A translated nav string that only appears for this locale


_LOCALE_SPECS: list[_LocaleSpec] = [
    _LocaleSpec(code="cs", label="Čeština",   nav_word="Mapa"),
    _LocaleSpec(code="de", label="Deutsch",   nav_word="Karte"),
    _LocaleSpec(code="es", label="Español",   nav_word="Mapa"),
    _LocaleSpec(code="fi", label="Suomi",     nav_word="Kartta"),
    _LocaleSpec(code="it", label="Italiano",  nav_word="Mappa"),
    _LocaleSpec(code="nb", label="Norsk",     nav_word="Kart"),
    _LocaleSpec(code="pt", label="Português", nav_word="Mapa"),
]


@pytest.mark.parametrize("spec", _LOCALE_SPECS, ids=[s.code for s in _LOCALE_SPECS])
async def test_locale_accepted_by_set_lang(spec: _LocaleSpec, async_client: httpx.AsyncClient) -> None:
    """/set-lang must redirect and set the wl_lang cookie for each locale."""
    resp = await async_client.get(f"/set-lang?lang={spec.code}", follow_redirects=False)
    assert resp.status_code == 302
    assert f"wl_lang={spec.code}" in resp.headers.get("set-cookie", "")


@pytest.mark.parametrize("spec", _LOCALE_SPECS, ids=[s.code for s in _LOCALE_SPECS])
async def test_locale_cookie_changes_html_lang(spec: _LocaleSpec, async_client: httpx.AsyncClient) -> None:
    """Setting wl_lang cookie must change the html lang= attribute."""
    resp = await async_client.get("/", cookies={"wl_lang": spec.code})
    assert resp.status_code == 200
    assert f'lang="{spec.code}"' in resp.text


@pytest.mark.parametrize("spec", _LOCALE_SPECS, ids=[s.code for s in _LOCALE_SPECS])
async def test_locale_nav_translated(spec: _LocaleSpec, async_client: httpx.AsyncClient) -> None:
    """At least one translated nav string must appear for the active locale."""
    resp = await async_client.get("/", cookies={"wl_lang": spec.code})
    assert resp.status_code == 200
    assert spec.nav_word in resp.text


@pytest.mark.parametrize("spec", _LOCALE_SPECS, ids=[s.code for s in _LOCALE_SPECS])
async def test_locale_label_in_dropdown(spec: _LocaleSpec, async_client: httpx.AsyncClient) -> None:
    """The locale's display label must appear in the language-selector dropdown."""
    resp = await async_client.get("/")
    assert spec.label in resp.text
