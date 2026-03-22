"""
Centralised registry mapping country codes to their dam description functions.

This eliminates the 13-branch if/elif dispatch that previously lived in
app/routes/pages.py, replacing it with a single dict lookup.

Each value is the existing per-country description function — all fallback
logic (generic prose for unknown dams) stays in those functions unchanged.
"""
from __future__ import annotations

from collections.abc import Callable

from app.at_dam_descriptions import get_at_dam_description
from app.bg_dam_descriptions import get_bg_dam_description
from app.ch_dam_descriptions import get_ch_dam_description
from app.cz_dam_descriptions import get_cz_dam_description
from app.dam_descriptions import get_dam_description as get_cy_dam_description
from app.de_dam_descriptions import get_de_dam_description
from app.es_dam_descriptions import get_es_dam_description
from app.fi_dam_descriptions import get_fi_dam_description
from app.gr_dam_descriptions import get_gr_dam_description
from app.it_dam_descriptions import get_it_dam_description
from app.no_dam_descriptions import get_no_dam_description
from app.pl_dam_descriptions import get_pl_dam_description
from app.pt_dam_descriptions import get_pt_dam_description

# Maps ISO 3166-1 alpha-2 country code → description lookup function.
# Cyprus uses "cy" as its key even though the legacy module omits the prefix.
DESCRIPTION_REGISTRY: dict[str, Callable[[str], str]] = {
    "cy": get_cy_dam_description,
    "gr": get_gr_dam_description,
    "es": get_es_dam_description,
    "pt": get_pt_dam_description,
    "cz": get_cz_dam_description,
    "at": get_at_dam_description,
    "it": get_it_dam_description,
    "fi": get_fi_dam_description,
    "no": get_no_dam_description,
    "ch": get_ch_dam_description,
    "bg": get_bg_dam_description,
    "de": get_de_dam_description,
    "pl": get_pl_dam_description,
}


def get_description(country: str, name_en: str) -> str:
    """Return the dam description for the given country and dam name.

    Falls back to empty string for unknown country codes so callers never
    need to guard against None.
    """
    fn = DESCRIPTION_REGISTRY.get(country)
    if fn is None:
        return ""
    return fn(name_en)
