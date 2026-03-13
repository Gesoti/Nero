"""
FastAPI application factory.
Lifespan handles: data dir creation, DB schema init, initial seed or
incremental sync on restart, and APScheduler for background refresh.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api_client import close_client
from app.config import settings
from app.i18n import install_i18n
from app.db import init_database, is_database_empty
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directory exists before SQLite opens the file
    Path("data").mkdir(exist_ok=True)

    init_database()

    if is_database_empty():
        logger.info("Empty database — running initial seed (this takes ~5-10s)")
        await initial_seed()
    else:
        logger.info("Existing database — running incremental sync")
        try:
            await incremental_sync()
        except Exception as exc:
            # Non-fatal: stale cache is better than a crashed startup
            logger.error("Startup incremental sync failed, serving cached data: %s", exc)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        incremental_sync,
        trigger="interval",
        hours=settings.sync_interval_hours,
        id="incremental_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started (every %dh)", settings.sync_interval_hours)

    yield

    scheduler.shutdown(wait=False)
    await close_client()
    logger.info("Shutdown complete")


app = FastAPI(title="Cyprus Water Levels", lifespan=lifespan)

app.middleware("http")(security_headers_middleware)
app.include_router(page_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> HTMLResponse:
    return _templates.TemplateResponse(request, "404.html", {}, status_code=404)
