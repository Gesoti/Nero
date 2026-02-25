"""E2E test configuration for Playwright.

Run against the live site:
    uv run pytest tests/e2e/ -m e2e_live --base-url https://nero.cy -v

Run against a local server (must be running on localhost:8000):
    uv run pytest tests/e2e/ -m e2e_local --base-url http://localhost:8000 -v
"""
