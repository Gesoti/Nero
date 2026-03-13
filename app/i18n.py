"""
Internationalization setup — Jinja2 i18n extension (English-only passthrough).

`install_i18n` wires the i18n extension onto a Jinja2 environment once at
startup using NullTranslations (English passthrough). _() calls in templates
return their input unchanged.

`get_translations` always returns NullTranslations (English-only mode).
Multilingual support was removed; this module exists to keep _() working
in templates as a no-op passthrough.
"""
from __future__ import annotations

import gettext

from jinja2 import Environment


def install_i18n(env: Environment) -> None:
    """Add the i18n extension and install passthrough translations."""
    env.add_extension("jinja2.ext.i18n")
    env.install_gettext_translations(gettext.NullTranslations())


def get_translations(locale: str) -> gettext.NullTranslations:
    """Return NullTranslations for any locale (English-only mode)."""
    return gettext.NullTranslations()
