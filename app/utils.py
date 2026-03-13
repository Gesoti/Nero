"""Shared utility functions."""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    """Convert a string to a URL-safe ASCII slug.

    Lowercases, removes non-alphanumeric chars (except hyphens),
    and collapses whitespace/hyphens into single hyphens.
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)  # remove non-word chars except hyphens
    value = re.sub(r"[-\s]+", "-", value)   # collapse whitespace/hyphens
    return value.strip("-")
