"""E2E smoke tests for the WaterLevels dashboard.

Run against the live site:
    uv run pytest tests/e2e/ -m e2e_live --base-url https://nero.cy -v

Run against a local server (must be running on localhost:8000):
    uv run pytest tests/e2e/ -m e2e_local --base-url http://localhost:8000 -v
"""

import re

import pytest
from playwright.sync_api import Page, expect


# ── Dashboard (/) ────────────────────────────────────────────────────────────


@pytest.mark.e2e_live
@pytest.mark.e2e_local
class TestDashboardSmoke:
    """Basic smoke tests for the main dashboard page."""

    def test_homepage_loads_200(self, page: Page) -> None:
        response = page.goto("/")
        assert response is not None
        assert response.status == 200

    def test_page_title_contains_nero(self, page: Page) -> None:
        page.goto("/")
        expect(page).to_have_title(re.compile(r".*Nero.*"))

    def test_dam_cards_rendered(self, page: Page) -> None:
        """At least one dam card link is visible on the dashboard."""
        page.goto("/")
        cards = page.locator('a[href^="/dam/"]')
        expect(cards.first).to_be_visible()

    def test_no_js_console_errors(self, page: Page) -> None:
        """No JavaScript errors appear in the browser console."""
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.goto("/", wait_until="networkidle")
        assert errors == [], f"JS console errors: {errors}"


# ── CSP Headers ──────────────────────────────────────────────────────────────


@pytest.mark.e2e_live
@pytest.mark.e2e_local
class TestCSPHeaders:
    """Verify Content Security Policy is present and in enforcement mode."""

    def test_csp_header_present(self, page: Page) -> None:
        response = page.goto("/")
        assert response is not None
        headers = response.headers
        csp = headers.get("content-security-policy", "")
        assert csp, "CSP header missing — check app/security.py"

    def test_csp_not_report_only(self, page: Page) -> None:
        """CSP must be enforced, not just report-only."""
        response = page.goto("/")
        assert response is not None
        headers = response.headers
        assert "content-security-policy" in headers, "No enforcement CSP header"

    def test_no_csp_violations_on_page(self, page: Page) -> None:
        """Load the page and check for CSP violation reports in console."""
        violations: list[str] = []

        def on_console(msg):
            text = msg.text.lower()
            if "content security policy" in text or "csp" in text:
                violations.append(msg.text)

        page.on("console", on_console)
        page.goto("/", wait_until="networkidle")
        assert violations == [], f"CSP violations detected: {violations}"


# ── Dam Detail Page ──────────────────────────────────────────────────────────


@pytest.mark.e2e_live
@pytest.mark.e2e_local
class TestDamDetailSmoke:
    """Smoke tests for individual dam pages."""

    def test_dam_page_loads(self, page: Page) -> None:
        response = page.goto("/dam/Kouris")
        assert response is not None
        assert response.status == 200

    def test_chart_canvas_rendered(self, page: Page) -> None:
        """Chart.js should render a canvas element on the dam detail page."""
        page.goto("/dam/Kouris", wait_until="networkidle")
        canvas = page.locator("canvas")
        expect(canvas.first).to_be_visible()


# ── Map Page ─────────────────────────────────────────────────────────────────


@pytest.mark.e2e_live
@pytest.mark.e2e_local
class TestMapSmoke:
    """Smoke tests for the Leaflet map page."""

    def test_map_page_loads(self, page: Page) -> None:
        response = page.goto("/map")
        assert response is not None
        assert response.status == 200

    def test_leaflet_map_container_rendered(self, page: Page) -> None:
        page.goto("/map", wait_until="networkidle")
        map_container = page.locator(".leaflet-container")
        expect(map_container).to_be_visible()
