"""
Page route handlers. Each handler reads from SQLite and renders a Jinja2 template.
Severity labels are computed here so templates stay logic-free.
"""
from __future__ import annotations

import json
import logging

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import settings

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

    pct_display = round(dam.percentage * 100, 1)
    meta_desc = (
        f"{dam.name_en} dam is at {pct_display}% capacity "
        f"({dam.storage_mcm:.1f} of {dam.capacity_mcm:.1f} MCM). "
        f"View historical trends and year-on-year comparisons."
    )

    return templates.TemplateResponse(
        request,
        "dam_detail.html",
        {
            "dam": dam,
            "severity": severity,
            "history_json": json.dumps(history),
            "meta_description": meta_desc,
        },
    )


@router.get("/map")
async def map_view(request: Request):
    dams_raw = get_all_dams_with_current_stats()
    dams = [
        {**dam.__dict__, "severity": get_severity(dam.percentage)}
        for dam in dams_raw
    ]
    return templates.TemplateResponse(
        request,
        "map.html",
        {"dams_json": json.dumps(dams)},
    )


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {})


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {})


@router.get("/ads.txt")
async def ads_txt():
    body = "google.com, pub-3066658032903900, DIRECT, f08c47fec0942fa0\n"
    return PlainTextResponse(body)


@router.get("/robots.txt")
async def robots_txt():
    base = settings.base_url.rstrip("/")
    body = (
        "User-agent: *\n"
        "Disallow: /health\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )
    return PlainTextResponse(body)


@router.get("/sitemap.xml")
async def sitemap_xml():
    base = settings.base_url.rstrip("/")
    dams = get_all_dams_with_current_stats()

    urls = ["/", "/map", "/about", "/privacy"]
    for dam in dams:
        urls.append(f"/dam/{quote(dam.name_en, safe='')}")

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        xml_parts.append(f"  <url><loc>{base}{url}</loc></url>")
    xml_parts.append("</urlset>")

    return Response(
        content="\n".join(xml_parts),
        media_type="application/xml",
    )


@router.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
