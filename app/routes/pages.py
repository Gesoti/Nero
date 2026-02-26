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

from app.blog import load_all_posts, load_post
from app.config import settings
from app.dam_descriptions import get_dam_description

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


def _canonical(path: str) -> str:
    """Build a canonical URL for the given path."""
    return f"{settings.base_url.rstrip('/')}{path}"


def _breadcrumbs(*items: tuple[str, str]) -> list[dict[str, str]]:
    """Build breadcrumb list from (name, path) tuples. Always starts with Home."""
    base = settings.base_url.rstrip("/")
    crumbs = [{"name": "Home", "url": f"{base}/"}]
    for name, path in items:
        crumbs.append({"name": name, "url": f"{base}{path}"})
    return crumbs


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
            "canonical_url": _canonical("/"),
            "breadcrumbs": _breadcrumbs(),
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

    # Related dams: up to 4 other dams, sorted by capacity (closest in size)
    all_dams = get_all_dams_with_current_stats()
    related = sorted(
        [d for d in all_dams if d.name_en != name_en],
        key=lambda d: abs(d.capacity_mcm - dam.capacity_mcm),
    )[:4]
    related_dams = [
        {"name_en": d.name_en, "percentage": round(d.percentage * 100, 1),
         "severity": get_severity(d.percentage)}
        for d in related
    ]

    return templates.TemplateResponse(
        request,
        "dam_detail.html",
        {
            "dam": dam,
            "severity": severity,
            "history_json": json.dumps(history),
            "meta_description": meta_desc,
            "dam_description": get_dam_description(name_en),
            "related_dams": related_dams,
            "canonical_url": _canonical(f"/dam/{quote(name_en, safe='')}"),
            "breadcrumbs": _breadcrumbs((name_en, f"/dam/{quote(name_en, safe='')}")),
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
        {"dams_json": json.dumps(dams), "canonical_url": _canonical("/map")},
    )


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request, "about.html", {"canonical_url": _canonical("/about")})


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"canonical_url": _canonical("/privacy")})


@router.get("/blog")
async def blog_index(request: Request):
    posts = load_all_posts()
    return templates.TemplateResponse(
        request,
        "blog_index.html",
        {"posts": posts, "canonical_url": _canonical("/blog"),
         "breadcrumbs": _breadcrumbs(("Blog", "/blog"))},
    )


@router.get("/blog/water-report-{year:int}-{month:int}")
async def monthly_report(request: Request, year: int, month: int):
    """Auto-generated monthly water report from DB data."""
    import calendar
    from dataclasses import dataclass as dc
    from datetime import date as date_type

    if month < 1 or month > 12 or year < 2009:
        raise HTTPException(status_code=404, detail="Invalid report date")

    month_name = calendar.month_name[month]
    dams_raw = get_all_dams_with_current_stats()
    totals = get_system_totals()

    if not totals:
        raise HTTPException(status_code=404, detail="No data available")

    pct = round(totals.total_percentage * 100, 1)
    severity = get_severity(totals.total_percentage)

    # Build dam summary sorted by percentage
    dam_rows: list[str] = []
    for dam in sorted(dams_raw, key=lambda d: d.percentage):
        dp = round(dam.percentage * 100, 1)
        sev = get_severity(dam.percentage)
        dam_rows.append(
            f"- **[{dam.name_en}](/dam/{quote(dam.name_en, safe='')})**: "
            f"{dp}% ({dam.storage_mcm:.1f} / {dam.capacity_mcm:.1f} MCM) — {sev}"
        )

    content_md = (
        f"The Cyprus reservoir system stands at **{pct}%** of total capacity as of "
        f"{month_name} {year}, with {totals.total_storage_mcm:.1f} MCM stored out of "
        f"a combined {totals.total_capacity_mcm:.1f} MCM across all 17 major dams.\n\n"
        f"Overall system status: **{severity}**.\n\n"
        f"## Dam-by-dam breakdown\n\n"
        + "\n".join(dam_rows)
        + "\n\n"
        f"## What this means\n\n"
        f"{'At ' + str(pct) + '% capacity, the system is in critical territory. ' if pct < 20 else ''}"
        f"{'Conservation measures and supply restrictions are in effect. ' if pct < 40 else ''}"
        f"For detailed historical trends, visit individual dam pages above or the "
        f"[main dashboard](/).\n\n"
        f"*Data sourced from the Water Development Department of Cyprus. "
        f"Updated every 6 hours.*"
    )

    import mistune
    _md = mistune.create_markdown(escape=False)

    @dc(frozen=True)
    class _ReportPost:
        title: str
        slug: str
        date: date_type
        description: str
        author: str
        content_html: str

    post = _ReportPost(
        title=f"Water Report — {month_name} {year}",
        slug=f"water-report-{year}-{month:02d}",
        date=date_type(year, month, 1),
        description=f"Monthly water report for Cyprus dams — {month_name} {year}. System at {pct}% capacity.",
        author="Nero Team",
        content_html=_md(content_md),
    )

    return templates.TemplateResponse(
        request,
        "blog_post.html",
        {"post": post, "canonical_url": _canonical(f"/blog/water-report-{year}-{month:02d}"),
         "breadcrumbs": _breadcrumbs(("Blog", "/blog"), (post.title, f"/blog/water-report-{year}-{month:02d}"))},
    )


@router.get("/blog/{slug}")
async def blog_post_page(request: Request, slug: str):
    post = load_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(
        request,
        "blog_post.html",
        {"post": post, "canonical_url": _canonical(f"/blog/{slug}"),
         "breadcrumbs": _breadcrumbs(("Blog", "/blog"), (post.title, f"/blog/{slug}"))},
    )


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
    from datetime import date as date_type

    base = settings.base_url.rstrip("/")
    dams = get_all_dams_with_current_stats()
    blog_posts = load_all_posts()
    today = date_type.today().isoformat()
    last_sync = get_last_sync_time()
    data_date = last_sync[:10] if last_sync else today

    def url_entry(path: str, changefreq: str, priority: str, lastmod: str | None = None) -> str:
        lm = lastmod or data_date
        return (
            f"  <url>\n"
            f"    <loc>{base}{path}</loc>\n"
            f"    <lastmod>{lm}</lastmod>\n"
            f"    <changefreq>{changefreq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        url_entry("/", "daily", "1.0"),
        url_entry("/map", "daily", "0.7"),
        url_entry("/blog", "weekly", "0.7"),
        url_entry("/about", "monthly", "0.3"),
        url_entry("/privacy", "monthly", "0.2"),
    ]
    for dam in dams:
        xml_parts.append(url_entry(f"/dam/{quote(dam.name_en, safe='')}", "daily", "0.8"))
    for post in blog_posts:
        xml_parts.append(url_entry(f"/blog/{post.slug}", "monthly", "0.6", lastmod=post.date.isoformat()))
    xml_parts.append("</urlset>")

    return Response(
        content="\n".join(xml_parts),
        media_type="application/xml",
    )


@router.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
