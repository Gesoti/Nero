"""
FastAPI application factory.
Lifespan handles: data dir creation, DB schema init, initial seed or
incremental sync on restart, and APScheduler for background refresh.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.i18n import install_i18n
from app.db import init_database, is_database_empty
from app.middleware.country import CountryPrefixMiddleware
from app.providers.base import DataProvider
from app.providers.cyprus import CyprusProvider
from app.providers.greece import GreeceProvider
from app.routes.pages import router as page_router
from app.security import security_headers_middleware
from app.sync import incremental_sync, initial_seed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_templates = Jinja2Templates(directory="app/templates")
install_i18n(_templates.env)

# Provider registry: country_code → (provider, db_path)
# Built at startup, used by lifespan and scheduler
_provider_registry: dict[str, tuple[DataProvider, str]] = {}


def _build_provider_registry() -> dict[str, tuple[DataProvider, str]]:
    """Construct a provider instance + db_path for each enabled country."""
    registry: dict[str, tuple[DataProvider, str]] = {}

    for cc in settings.get_enabled_countries():
        db_path = f"data/{cc}/water.db"

        _timeout = httpx.Timeout(
            connect=5.0,
            read=settings.upstream_timeout_seconds,
            write=5.0,
            pool=5.0,
        )

        if cc == "cy":
            client = httpx.AsyncClient(
                base_url=settings.upstream_base_url,
                headers={"User-Agent": "CyprusWaterDashboard/1.0"},
                timeout=_timeout,
            )
            registry[cc] = (CyprusProvider(client=client), db_path)
        elif cc == "gr":
            client = httpx.AsyncClient(
                base_url="https://opendata-api-eydap.growthfund.gr",
                headers={"User-Agent": "NeroWaterDashboard/1.0"},
                timeout=_timeout,
            )
            registry[cc] = (GreeceProvider(client=client), db_path)
        else:
            logger.warning("No provider implemented for country '%s' — skipping", cc)

    return registry


async def _sync_all_countries() -> None:
    """Run incremental_sync for every enabled country. Used by APScheduler."""
    for cc, (provider, db_path) in _provider_registry.items():
        try:
            await incremental_sync(provider=provider, db_path=db_path)
        except Exception as exc:
            logger.error("Incremental sync failed for %s: %s", cc, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _provider_registry

    # Ensure data directory exists before SQLite opens the file
    Path("data").mkdir(exist_ok=True)

    _provider_registry = _build_provider_registry()

    # Init + seed/sync each enabled country
    for cc, (provider, db_path) in _provider_registry.items():
        init_database(db_path=db_path)

        if is_database_empty(db_path=db_path):
            logger.info("[%s] Empty database — running initial seed", cc)
            await initial_seed(provider=provider, db_path=db_path)
        else:
            logger.info("[%s] Existing database — running incremental sync", cc)
            try:
                await incremental_sync(provider=provider, db_path=db_path)
            except Exception as exc:
                logger.error("[%s] Startup sync failed, serving cached data: %s", cc, exc)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _sync_all_countries,
        trigger="interval",
        hours=settings.sync_interval_hours,
        id="sync_all_countries",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started (every %dh)", settings.sync_interval_hours)

    yield

    scheduler.shutdown(wait=False)
    for _cc, (provider, _db_path) in _provider_registry.items():
        await provider.close()
    _provider_registry.clear()
    logger.info("Shutdown complete")


app = FastAPI(title="Cyprus Water Levels", lifespan=lifespan)

# Country-prefix middleware must run first so that route matching sees the
# stripped path. Security headers middleware wraps it on the outside.
app.add_middleware(
    CountryPrefixMiddleware,
    enabled_countries=settings.get_enabled_countries(),
    default_country="cy",
)
app.middleware("http")(security_headers_middleware)
app.include_router(page_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> HTMLResponse:
    country: str = getattr(request.state, "country", settings.country)
    return _templates.TemplateResponse(
        request,
        "404.html",
        {"layout_template": f"{country}/layout.html"},
        status_code=404,
    )
