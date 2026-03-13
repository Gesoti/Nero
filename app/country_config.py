"""Country-specific configuration constants.

Each country code maps to its locale, default DB path, and map centre
coordinates. This module is import-safe (no heavy dependencies) so it can
be used in both middleware and route layers without circular imports.
"""
from __future__ import annotations

# BCP-47 locale tag used for Babel i18n and HTML lang attribute
COUNTRY_LOCALE_MAP: dict[str, str] = {
    "cy": "en",
    "gr": "en",
}

# Canonical per-country SQLite database paths (relative to repo root)
COUNTRY_DB_PATHS: dict[str, str] = {
    "cy": "data/cy/water.db",
    "gr": "data/gr/water.db",
}

# Human-readable country labels for navigation UI
COUNTRY_LABELS: dict[str, str] = {
    "cy": "Cyprus",
    "gr": "Greece",
}

# (lat, lng) map centre for the Leaflet map on /map
COUNTRY_MAP_CENTRES: dict[str, tuple[float, float]] = {
    "cy": (34.917, 33.0),
    "gr": (38.5, 22.5),
}
