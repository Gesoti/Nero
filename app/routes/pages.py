"""
Page route handlers. Each handler reads from SQLite and renders a Jinja2 template.
Severity labels are computed here so templates stay logic-free.

Per-request wiring (G10):
- db_path comes from request.state.db_path (set by CountryPrefixMiddleware)
- layout_template is derived from request.state.country
- i18n translations are installed per-request based on request.state.locale
- dam descriptions use the country-appropriate module
"""
from __future__ import annotations

import json
import logging

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.blog import load_all_posts, load_post
from app.config import settings
from app.country_config import COUNTRY_LABELS, COUNTRY_LOCALE_MAP, COUNTRY_MAP_CENTRES
from app.at_dam_descriptions import get_at_dam_description
from app.cz_dam_descriptions import get_cz_dam_description
from app.dam_descriptions import get_dam_description
from app.es_dam_descriptions import get_es_dam_description
from app.fi_dam_descriptions import get_fi_dam_description
from app.it_dam_descriptions import get_it_dam_description
from app.no_dam_descriptions import get_no_dam_description
from app.pt_dam_descriptions import get_pt_dam_description
from app.gr_dam_descriptions import get_gr_dam_description
from app.i18n import install_i18n, get_translations, SUPPORTED_LOCALES, LANGUAGE_FLAGS, LANGUAGE_LABELS

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
install_i18n(templates.env)


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


def _get_dam_description_for_country(country: str, name_en: str) -> str:
    """Return the dam description from the correct country module."""
    if country == "gr":
        return get_gr_dam_description(name_en)
    if country == "es":
        return get_es_dam_description(name_en)
    if country == "pt":
        return get_pt_dam_description(name_en)
    if country == "cz":
        return get_cz_dam_description(name_en)
    if country == "at":
        return get_at_dam_description(name_en)
    if country == "it":
        return get_it_dam_description(name_en)
    if country == "fi":
        return get_fi_dam_description(name_en)
    if country == "no":
        return get_no_dam_description(name_en)
    return get_dam_description(name_en)


def _build_hreflang_alternates(country: str, request_path: str) -> list[dict[str, str]]:
    """
    Build a list of hreflang alternate link dicts for all enabled countries.

    Each entry has 'lang' (BCP-47) and 'href' (absolute URL). The current
    country is included so search engines see a complete self-referential set.
    Cross-country path mapping: strip the current country prefix, then prepend
    the alternate country's prefix.
    """
    base = settings.base_url.rstrip("/")
    enabled = settings.get_enabled_countries()
    if len(enabled) <= 1:
        # Single-country deployment — no cross-links needed
        return []

    # Determine the path without any country prefix (canonical CY path)
    # e.g. "/gr/map" → "/map", "/map" → "/map"
    cy_path = request_path
    for c in enabled:
        if c != "cy":
            prefix = f"/{c}"
            if cy_path.startswith(prefix + "/") or cy_path == prefix:
                cy_path = cy_path[len(prefix):]
                if not cy_path:
                    cy_path = "/"
                break

    alternates: list[dict[str, str]] = []
    for c in enabled:
        lang = COUNTRY_LOCALE_MAP.get(c, "en")
        if c == "cy":
            href = f"{base}{cy_path}"
        else:
            # Add country prefix; handle root path specially
            path_with_prefix = f"/{c}{cy_path}" if cy_path != "/" else f"/{c}/"
            href = f"{base}{path_with_prefix}"
        alternates.append({"lang": lang, "href": href})

    return alternates


def _render_ctx(request: Request, extra: dict) -> dict:
    """
    Build a base template context with per-request country wiring.

    Installs the correct translations onto the shared Jinja2 environment
    before each render so that _() calls resolve to the right locale.
    Language is determined by the user's wl_lang cookie (default: English).
    This is safe for our single-worker dev server and acceptable for
    production (workers are single-threaded per request in Uvicorn/Gunicorn).
    """
    country: str = getattr(request.state, "country", settings.country)
    country_prefix: str = getattr(request.state, "country_prefix", "")

    # Language preference: cookie > default (en)
    lang = request.cookies.get("wl_lang", "en")
    if lang not in SUPPORTED_LOCALES:
        lang = "en"

    # Install correct translations for this request before Jinja2 renders.
    templates.env.install_gettext_translations(get_translations(lang))

    # Build language navigation data for the dropdown
    available_langs = [
        {"code": code, "label": label, "flag": LANGUAGE_FLAGS.get(code, code)}
        for code, label in LANGUAGE_LABELS.items()
    ]

    # Build country navigation data for the nav bar — preserves current page path
    # so switching countries on /map stays on /map, not redirecting to /
    enabled = settings.get_enabled_countries()
    current_path = request.url.path
    # Strip country prefix to get the page-relative path (e.g., /gr/map → /map)
    page_path = current_path
    if country_prefix and current_path.startswith(country_prefix):
        page_path = current_path[len(country_prefix):] or "/"

    country_nav_with_path = [
        {
            "code": cc,
            "label": COUNTRY_LABELS.get(cc, cc.upper()),
            "href": (f"/{cc}{page_path}" if cc != "cy" else page_path) if page_path != "/" else (f"/{cc}/" if cc != "cy" else "/"),
        }
        for cc in enabled
    ] if len(enabled) > 1 else []

    ctx = {
        "layout_template": f"{country}/layout.html",
        "country_prefix": country_prefix,
        "country": country,
        "country_label": COUNTRY_LABELS.get(country, country.upper()),
        "country_nav": country_nav_with_path,
        "current_lang": lang,
        "current_lang_label": LANGUAGE_LABELS.get(lang, "English"),
        "current_lang_flag": LANGUAGE_FLAGS.get(lang, lang),
        "available_langs": available_langs,
        # hreflang_alternates is a list of {lang, href} dicts for cross-country links.
        # Empty for single-country deployments; populated when multiple countries enabled.
        "hreflang_alternates": _build_hreflang_alternates(country, request.url.path),
    }
    ctx.update(extra)
    return ctx


@router.get("/")
async def dashboard(request: Request):
    db_path: str = getattr(request.state, "db_path", "")
    dams_raw = get_all_dams_with_current_stats(db_path=db_path)
    dams = [
        {**dam.__dict__, "severity": get_severity(dam.percentage)}
        for dam in dams_raw
    ]
    totals = get_system_totals(db_path=db_path)
    system_history = get_system_history(db_path=db_path)
    last_updated = get_last_sync_time(db_path=db_path)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _render_ctx(request, {
            "dams": dams,
            "totals": totals,
            "system_history_json": json.dumps(system_history),
            "last_updated": last_updated,
            "canonical_url": _canonical("/"),
            "breadcrumbs": _breadcrumbs(),
        }),
    )


@router.get("/dam/{name_en}")
async def dam_detail_page(request: Request, name_en: str):
    db_path: str = getattr(request.state, "db_path", "")
    country: str = getattr(request.state, "country", settings.country)

    dam = get_dam_detail(name_en, db_path=db_path)
    if not dam:
        raise HTTPException(status_code=404, detail="Dam not found")

    history = get_dam_history(name_en, db_path=db_path)
    severity = get_severity(dam.percentage)

    pct_display = round(dam.percentage * 100, 1)
    meta_desc = (
        f"{dam.name_en} dam is at {pct_display}% capacity "
        f"({dam.storage_mcm:.1f} of {dam.capacity_mcm:.1f} MCM). "
        f"View historical trends and year-on-year comparisons."
    )

    # Related dams: up to 4 other dams, sorted by capacity (closest in size)
    all_dams = get_all_dams_with_current_stats(db_path=db_path)
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
        _render_ctx(request, {
            "dam": dam,
            "severity": severity,
            "history_json": json.dumps(history),
            "meta_description": meta_desc,
            "dam_description": _get_dam_description_for_country(country, name_en),
            "related_dams": related_dams,
            "canonical_url": _canonical(f"/dam/{quote(name_en, safe='')}"),
            "breadcrumbs": _breadcrumbs((name_en, f"/dam/{quote(name_en, safe='')}")),
        }),
    )


@router.get("/map")
async def map_view(request: Request):
    db_path: str = getattr(request.state, "db_path", "")
    country: str = getattr(request.state, "country", settings.country)
    dams_raw = get_all_dams_with_current_stats(db_path=db_path)
    dams = [
        {**dam.__dict__, "severity": get_severity(dam.percentage)}
        for dam in dams_raw
    ]
    # Zoom level 8 suits the compact extent of Cyprus; Greece's reservoirs
    # are more spread out so zoom 7 fits better.
    map_zoom: dict[str, int] = {"cy": 9, "gr": 7, "es": 6, "pt": 7, "cz": 7, "at": 7, "it": 8, "fi": 5}
    centre = COUNTRY_MAP_CENTRES.get(country, COUNTRY_MAP_CENTRES["cy"])
    return templates.TemplateResponse(
        request,
        "map.html",
        _render_ctx(request, {
            "dams_json": json.dumps(dams),
            "map_center_lat": centre[0],
            "map_center_lng": centre[1],
            "map_zoom": map_zoom.get(country, 9),
            "canonical_url": _canonical("/map"),
        }),
    )


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        _render_ctx(request, {"canonical_url": _canonical("/about")}),
    )


@router.get("/privacy")
async def privacy(request: Request):
    return templates.TemplateResponse(
        request,
        "privacy.html",
        _render_ctx(request, {"canonical_url": _canonical("/privacy")}),
    )


@router.get("/blog")
async def blog_index(request: Request):
    import calendar
    from datetime import date as date_type

    posts = load_all_posts()

    # Generate available monthly report links (from 2024-01 to current month)
    today = date_type.today()
    report_months: list[dict[str, str]] = []
    year, month = today.year, today.month
    while (year, month) >= (2024, 1):
        month_name = calendar.month_name[month]
        report_months.append({
            "label": f"{month_name} {year}",
            "url": f"/blog/water-report-{year}-{month:02d}",
        })
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return templates.TemplateResponse(
        request,
        "blog_index.html",
        _render_ctx(request, {
            "posts": posts,
            "report_months": report_months,
            "canonical_url": _canonical("/blog"),
            "breadcrumbs": _breadcrumbs(("Blog", "/blog")),
        }),
    )


@router.get("/blog/water-report-{year:int}-{month:int}")
async def monthly_report(request: Request, year: int, month: int):
    """Auto-generated monthly water report from DB data."""
    import calendar
    from dataclasses import dataclass as dc
    from datetime import date as date_type

    if month < 1 or month > 12 or year < 2009:
        raise HTTPException(status_code=404, detail="Invalid report date")

    db_path: str = getattr(request.state, "db_path", "")
    month_name = calendar.month_name[month]
    dams_raw = get_all_dams_with_current_stats(db_path=db_path)
    totals = get_system_totals(db_path=db_path)

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
    _md = mistune.create_markdown(escape=True)

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
        _render_ctx(request, {
            "post": post,
            "noindex": True,
            "canonical_url": _canonical(f"/blog/water-report-{year}-{month:02d}"),
            "breadcrumbs": _breadcrumbs(
                ("Blog", "/blog"),
                (post.title, f"/blog/water-report-{year}-{month:02d}"),
            ),
        }),
    )


@router.get("/blog/{slug}")
async def blog_post_page(request: Request, slug: str):
    post = load_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse(
        request,
        "blog_post.html",
        _render_ctx(request, {
            "post": post,
            "canonical_url": _canonical(f"/blog/{slug}"),
            "breadcrumbs": _breadcrumbs(("Blog", "/blog"), (post.title, f"/blog/{slug}")),
        }),
    )


@router.get("/learn/how-dams-work")
async def learn_how_dams_work(request: Request):
    return templates.TemplateResponse(
        request,
        "learn_how_dams_work.html",
        _render_ctx(request, {
            "canonical_url": _canonical("/learn/how-dams-work"),
            "breadcrumbs": _breadcrumbs(
                ("Learn", "/learn/how-dams-work"),
                ("How Dams Work", "/learn/how-dams-work"),
            ),
        }),
    )


@router.get("/learn/water-crisis-history")
async def learn_water_crisis_history(request: Request):
    return templates.TemplateResponse(
        request,
        "learn_water_crisis_history.html",
        _render_ctx(request, {
            "canonical_url": _canonical("/learn/water-crisis-history"),
            "breadcrumbs": _breadcrumbs(
                ("Learn", "/learn/water-crisis-history"),
                ("Water Crisis History", "/learn/water-crisis-history"),
            ),
        }),
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
    from app.country_config import COUNTRY_DB_PATHS

    base = settings.base_url.rstrip("/")
    blog_posts = load_all_posts()
    today = date_type.today().isoformat()

    # Use the default CY db for the last-sync date stamp
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
        url_entry("/learn/how-dams-work", "monthly", "0.5"),
        url_entry("/learn/water-crisis-history", "monthly", "0.5"),
        url_entry("/privacy", "monthly", "0.2"),
    ]

    # CY dam pages (default country, no prefix) — queried from database
    cy_db = COUNTRY_DB_PATHS.get("cy", settings.db_path)
    cy_dams = get_all_dams_with_current_stats(db_path=cy_db)
    for dam in cy_dams:
        xml_parts.append(url_entry(f"/dam/{quote(dam.name_en, safe='')}", "daily", "0.8"))

    for post in [p for p in blog_posts if not getattr(p, "country", None) or p.country == "cy"]:
        xml_parts.append(url_entry(f"/blog/{post.slug}", "monthly", "0.6", lastmod=post.date.isoformat()))

    # Per-country pages for every enabled non-default country
    for country in settings.get_enabled_countries():
        if country == "cy":
            # Already handled above as the default (no prefix) country
            continue
        prefix = f"/{country}"
        xml_parts.append(url_entry(f"{prefix}/", "daily", "0.9"))
        xml_parts.append(url_entry(f"{prefix}/map", "daily", "0.7"))
        xml_parts.append(url_entry(f"{prefix}/about", "monthly", "0.3"))
        xml_parts.append(url_entry(f"{prefix}/blog", "weekly", "0.7"))

        # Greece dam names come from the provider's static metadata so the
        # sitemap is correct even when the gr database hasn't been seeded yet.
        # For future countries, fall back to querying their own database.
        if country == "gr":
            from app.providers.greece import _GREECE_DAMS as _gr_dams
            for dam_info in _gr_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "es":
            from app.providers.spain import _SPAIN_DAMS as _es_dams
            for dam_info in _es_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "pt":
            from app.providers.portugal import _PORTUGAL_DAMS as _pt_dams
            for dam_info in _pt_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "cz":
            from app.providers.czech import _CZECH_DAMS as _cz_dams
            for dam_info in _cz_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "at":
            from app.providers.austria import _AUSTRIA_DAMS as _at_dams
            for dam_info in _at_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "it":
            from app.providers.italy import _ITALY_DAMS as _it_dams
            for dam_info in _it_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        elif country == "fi":
            from app.providers.finland import _FINLAND_DAMS as _fi_dams
            for dam_info in _fi_dams:
                xml_parts.append(
                    url_entry(f"{prefix}/dam/{quote(dam_info.name_en, safe='')}", "daily", "0.8")
                )
        else:
            country_db = COUNTRY_DB_PATHS.get(country, "")
            if country_db:
                country_dams = get_all_dams_with_current_stats(db_path=country_db)
                for dam in country_dams:
                    xml_parts.append(
                        url_entry(f"{prefix}/dam/{quote(dam.name_en, safe='')}", "daily", "0.8")
                    )

        # Blog posts belonging to this country
        for post in [p for p in blog_posts if getattr(p, "country", None) == country]:
            xml_parts.append(
                url_entry(f"{prefix}/blog/{post.slug}", "monthly", "0.6", lastmod=post.date.isoformat())
            )

    xml_parts.append("</urlset>")

    return Response(
        content="\n".join(xml_parts),
        media_type="application/xml",
    )


import re

_SAFE_REDIRECT_RE = re.compile(r"^/[^/\\]")


def _safe_redirect(next_url: str) -> str:
    """Accept only relative paths that start with a single /."""
    if next_url and _SAFE_REDIRECT_RE.match(next_url):
        return next_url
    return "/"


@router.get("/set-lang")
async def set_language(lang: str = "en", next: str = "/"):
    """Set the user's language preference cookie and redirect back."""
    if lang not in SUPPORTED_LOCALES:
        lang = "en"
    safe_next = _safe_redirect(next)
    response = RedirectResponse(url=safe_next, status_code=302)
    response.set_cookie(
        key="wl_lang",
        value=lang,
        max_age=31536000,  # 1 year
        path="/",
        samesite="lax",
        httponly=True,
        secure=True,
    )
    return response


@router.get("/health")
async def health():
    return JSONResponse({"status": "ok"})
