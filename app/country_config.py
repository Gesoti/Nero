"""Country-specific configuration constants.

Each country code maps to its locale, default DB path, and map centre
coordinates. This module is import-safe (no heavy dependencies) so it can
be used in both middleware and route layers without circular imports.
"""
from __future__ import annotations

# BCP-47 locale tag used for Babel i18n and HTML lang attribute
COUNTRY_LOCALE_MAP: dict[str, str] = {
    "cy": "en",
    "gr": "el",
    "es": "es",
    "pt": "pt",
    "cz": "cs",
    "at": "de",
    "it": "it",
    "fi": "fi",
    "no": "nb",
    "ch": "de",
    "bg": "bg",
    "de": "de",
    "pl": "pl",
}

# Canonical per-country SQLite database paths (relative to repo root)
COUNTRY_DB_PATHS: dict[str, str] = {
    "cy": "data/cy/water.db",
    "gr": "data/gr/water.db",
    "es": "data/es/water.db",
    "pt": "data/pt/water.db",
    "cz": "data/cz/water.db",
    "at": "data/at/water.db",
    "it": "data/it/water.db",
    "fi": "data/fi/water.db",
    "no": "data/no/water.db",
    "ch": "data/ch/water.db",
    "bg": "data/bg/water.db",
    "de": "data/de/water.db",
    "pl": "data/pl/water.db",
}

# Human-readable country labels for navigation UI
COUNTRY_LABELS: dict[str, str] = {
    "cy": "Cyprus",
    "gr": "Greece",
    "es": "Spain",
    "pt": "Portugal",
    "cz": "Czech Republic",
    "at": "Austria",
    "it": "Italy",
    "fi": "Finland",
    "no": "Norway",
    "ch": "Switzerland",
    "bg": "Bulgaria",
    "de": "Germany",
    "pl": "Poland",
}

# (lat, lng) map centre for the Leaflet map on /map
COUNTRY_MAP_CENTRES: dict[str, tuple[float, float]] = {
    "cy": (34.917, 33.0),
    "gr": (38.5, 22.5),
    "es": (39.5, -3.5),
    "pt": (39.5, -8.0),
    "cz": (49.8, 15.5),
    "at": (47.5, 14.0),
    "it": (37.5, 14.0),
    "fi": (64.0, 26.0),
    "no": (65.0, 15.0),
    "ch": (46.8, 8.2),
    "bg": (42.7, 25.5),
    "de": (51.0, 10.5),
    "pl": (52.0, 19.5),
}
