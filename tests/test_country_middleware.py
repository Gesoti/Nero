"""
Tests for CountryPrefixMiddleware (G9).

The middleware strips /{country_code} prefixes from paths so that routes
remain unchanged, and injects country/locale/db_path into scope["state"].
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio

from app.config import settings
from app.main import app


@pytest_asyncio.fixture
async def multi_country_client(in_memory_db):
    """Client with enabled_countries=cy,gr so the /gr/ prefix is active."""
    with patch.object(settings, "enabled_countries", "cy,gr"):
        # Re-register the middleware with gr enabled by rebuilding the app
        # middleware stack.  Because CountryPrefixMiddleware reads its
        # enabled_countries at construction time (in app/main.py at import),
        # we patch settings before app startup and rebuild from the current
        # settings value via the middleware's own path.
        from app.middleware.country import CountryPrefixMiddleware

        # Wrap the bare app in a fresh middleware instance that sees gr.
        wrapped = CountryPrefixMiddleware(
            app=app,
            enabled_countries=settings.get_enabled_countries(),
            default_country="cy",
        )
        transport = httpx.ASGITransport(app=wrapped)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            yield client


# ── Baseline: default country (cy) still works ───────────────────────────────


async def test_health_no_prefix_returns_200(async_client: httpx.AsyncClient) -> None:
    """GET /health with no prefix returns 200 — middleware is a no-op for cy."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200


# ── /gr/ prefix handling ──────────────────────────────────────────────────────


async def test_gr_health_returns_200(
    multi_country_client: httpx.AsyncClient,
) -> None:
    """GET /gr/health strips prefix and hits the /health route."""
    resp = await multi_country_client.get("/gr/health")
    assert resp.status_code == 200


async def test_gr_root_returns_200(
    multi_country_client: httpx.AsyncClient,
) -> None:
    """GET /gr/ strips prefix and hits the / route."""
    resp = await multi_country_client.get("/gr/")
    # 200 or redirect — must not be 404
    assert resp.status_code != 404


# ── Static files must pass through untouched ─────────────────────────────────


async def test_static_files_unaffected(async_client: httpx.AsyncClient) -> None:
    """Static files served at /static/ must still respond (not 404)."""
    resp = await async_client.get("/static/css/tailwind.min.css")
    assert resp.status_code == 200


# ── country_config module ─────────────────────────────────────────────────────


def test_country_config_has_cy() -> None:
    from app.country_config import COUNTRY_MAP_CENTRES

    assert "cy" in COUNTRY_MAP_CENTRES


def test_country_config_has_gr() -> None:
    from app.country_config import COUNTRY_MAP_CENTRES

    assert "gr" in COUNTRY_MAP_CENTRES


def test_country_locale_map_cy_is_en() -> None:
    from app.country_config import COUNTRY_LOCALE_MAP

    assert COUNTRY_LOCALE_MAP["cy"] == "en"


def test_country_locale_map_gr_is_en() -> None:
    from app.country_config import COUNTRY_LOCALE_MAP

    assert COUNTRY_LOCALE_MAP["gr"] == "en"


# ── Middleware unit: scope["state"] injection ─────────────────────────────────


async def test_middleware_sets_country_cy_for_root_path() -> None:
    """Middleware injects country=cy into scope state for unprefixed paths."""
    from app.middleware.country import CountryPrefixMiddleware

    received_state: dict = {}

    async def capture_app(scope, receive, send):
        received_state.update(scope.get("state", {}))

    mw = CountryPrefixMiddleware(
        app=capture_app, enabled_countries=["cy", "gr"], default_country="cy"
    )
    scope = {"type": "http", "path": "/", "state": {}}
    await mw(scope, None, None)  # type: ignore[arg-type]
    assert received_state["country"] == "cy"
    assert received_state["locale"] == "en"
    assert received_state["country_prefix"] == ""


async def test_middleware_sets_country_gr_for_gr_prefix() -> None:
    """Middleware injects country=gr and strips /gr prefix."""
    from app.middleware.country import CountryPrefixMiddleware

    received_scope: dict = {}

    async def capture_app(scope, receive, send):
        received_scope.update(scope)

    mw = CountryPrefixMiddleware(
        app=capture_app, enabled_countries=["cy", "gr"], default_country="cy"
    )
    scope = {"type": "http", "path": "/gr/dams", "state": {}}
    await mw(scope, None, None)  # type: ignore[arg-type]

    assert received_scope["path"] == "/dams"
    assert received_scope["state"]["country"] == "gr"
    assert received_scope["state"]["locale"] == "en"
    assert received_scope["state"]["country_prefix"] == "/gr"


async def test_middleware_strips_gr_prefix_root() -> None:
    """GET /gr (no trailing slash) resolves path to /."""
    from app.middleware.country import CountryPrefixMiddleware

    received_scope: dict = {}

    async def capture_app(scope, receive, send):
        received_scope.update(scope)

    mw = CountryPrefixMiddleware(
        app=capture_app, enabled_countries=["cy", "gr"], default_country="cy"
    )
    scope = {"type": "http", "path": "/gr", "state": {}}
    await mw(scope, None, None)  # type: ignore[arg-type]

    assert received_scope["path"] == "/"
    assert received_scope["state"]["country"] == "gr"


async def test_middleware_passes_through_non_http_scopes() -> None:
    """Lifespan/websocket scopes must be forwarded without modification."""
    from app.middleware.country import CountryPrefixMiddleware

    forwarded: list[dict] = []

    async def capture_app(scope, receive, send):
        forwarded.append(scope)

    mw = CountryPrefixMiddleware(
        app=capture_app, enabled_countries=["cy", "gr"], default_country="cy"
    )
    scope = {"type": "lifespan"}
    await mw(scope, None, None)  # type: ignore[arg-type]

    assert forwarded[0]["type"] == "lifespan"
    assert "state" not in forwarded[0]
