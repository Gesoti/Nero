"""
Internationalization setup — Babel + Jinja2 i18n extension.

`install_i18n` wires the i18n extension onto a Jinja2 environment once at
startup using NullTranslations (English passthrough).

`get_translations` returns the correct gettext translations object for a
given locale, used by route handlers to install per-request translations
before rendering.
"""
from __future__ import annotations

import gettext

from jinja2 import Environment


def install_i18n(env: Environment) -> None:
    """Add the i18n extension and install passthrough translations."""
    env.add_extension("jinja2.ext.i18n")
    # NullTranslations returns msgid unchanged — perfect for English source strings
    env.install_gettext_translations(gettext.NullTranslations())


def get_translations(locale: str) -> gettext.NullTranslations:
    """
    Return the translations object for the given locale.

    For English (and any unrecognised locale) we use NullTranslations —
    a passthrough that returns msgids unchanged.  For other locales we load
    the compiled .mo file from app/translations/{locale}/LC_MESSAGES/.
    """
    if locale == "en":
        return gettext.NullTranslations()
    try:
        return gettext.translation(
            "messages",
            localedir="app/translations",
            languages=[locale],
        )
    except FileNotFoundError:
        # Fall back to passthrough if the .mo file is missing so the app
        # does not crash — strings will appear in English.
        return gettext.NullTranslations()
