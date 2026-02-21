"""
Page route handlers. Each handler reads from SQLite and renders a Jinja2 template.
Severity labels are computed here so templates stay logic-free.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.db import (
    get_all_dams_with_current_stats,
    get_dam_detail,
    get_dam_history,
    get_last_sync_time,
    get_severity,
    get_system_history,
    get_system_totals,
)

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def dashboard(request: Request):
    dams_raw = get_all_dams_with_current_stats()
    dams = [
        {**dam.__dict__, "severity": get_severity(dam.percentage)}
        for dam in dams_raw
    ]
    totals = get_system_totals()
    system_history = get_system_history()
    last_updated = get_last_sync_time()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "dams": dams,
            "totals": totals,
            "system_history_json": json.dumps(system_history),
            "last_updated": last_updated,
        },
    )


@router.get("/dam/{name_en}")
async def dam_detail_page(request: Request, name_en: str):
    dam = get_dam_detail(name_en)
    if not dam:
        raise HTTPException(status_code=404, detail="Dam not found")

    history = get_dam_history(name_en)
    severity = get_severity(dam.percentage)

    return templates.TemplateResponse(
        request,
        "dam_detail.html",
        {
            "dam": dam,
            "severity": severity,
            "history_json": json.dumps(history),
        },
    )


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {})


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


@router.get("/health")
async def health():
    last_sync = get_last_sync_time()
    return JSONResponse({"status": "ok", "last_sync": last_sync})
