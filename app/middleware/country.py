"""
ASGI middleware that detects a country-code prefix in the URL path,
strips it so that downstream routes remain unchanged, and injects
country/locale/db_path into scope["state"].

Why pure ASGI (not Starlette's BaseHTTPMiddleware)?
BaseHTTPMiddleware wraps the response body in a buffering layer which
causes issues with streaming responses and has known edge-cases with
exception propagation. A raw ASGI class avoids both problems.
"""
from __future__ import annotations

from app.country_config import COUNTRY_DB_PATHS, COUNTRY_LOCALE_MAP
from starlette.types import ASGIApp, Receive, Scope, Send


class CountryPrefixMiddleware:
    """
    Strip a leading /{country_code} prefix from HTTP paths and inject
    country metadata into scope["state"].

    The default country (cy) has no URL prefix — it serves from /.
    All other enabled countries get a /{cc} prefix (e.g. /gr/).
    """

    def __init__(
        self,
        app: ASGIApp,
        enabled_countries: list[str],
        default_country: str = "cy",
    ) -> None:
        self.app = app
        self.default_country = default_country
        # Only non-default countries get a URL prefix.
        self.country_prefixes: dict[str, str] = {
            f"/{cc}": cc for cc in enabled_countries if cc != default_country
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Non-HTTP scopes (lifespan, websocket) pass through unmodified.
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        path: str = scope["path"]
        country = self.default_country

        for prefix, cc in self.country_prefixes.items():
            if path == prefix or path.startswith(prefix + "/"):
                country = cc
                # Strip the country prefix; fall back to "/" when nothing remains.
                new_path = path[len(prefix):] or "/"
                # scope is an immutable MutableMapping in Starlette — copy to mutate.
                scope = dict(scope)
                scope["path"] = new_path
                # raw_path is the URL-encoded bytes form; keep it consistent.
                if "raw_path" in scope:
                    scope["raw_path"] = new_path.encode("utf-8")
                break

        # Inject country metadata so route handlers can access via request.state.
        # If an outer middleware (e.g. a test wrapper) already resolved the country,
        # do not overwrite it — the outer layer has the authoritative value.
        scope.setdefault("state", {})
        if "country" not in scope["state"]:
            scope["state"]["country"] = country
            scope["state"]["db_path"] = COUNTRY_DB_PATHS.get(country, f"data/{country}/water.db")
            scope["state"]["locale"] = COUNTRY_LOCALE_MAP.get(country, "en")
            # Prefix is empty string for the default country so templates can use it
            # directly: href="{{ request.state.country_prefix }}/dam/{{ name }}"
            scope["state"]["country_prefix"] = (
                "" if country == self.default_country else f"/{country}"
            )
        else:
            # Outer middleware already set country — only update path, not metadata.
            pass

        await self.app(scope, receive, send)
