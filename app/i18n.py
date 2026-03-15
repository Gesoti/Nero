"""
Internationalization setup — Jinja2 i18n extension with Babel translations.

`install_i18n` wires the i18n extension onto a Jinja2 environment once at
startup. `get_translations` loads compiled .mo files for non-English locales
and caches them via lru_cache for the lifetime of the process.

Supported locales are defined in SUPPORTED_LOCALES. Unknown locale values
fall back to English (NullTranslations).
"""
from __future__ import annotations

import gettext
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment

_TRANSLATIONS_DIR = Path(__file__).parent / "translations"

SUPPORTED_LOCALES: frozenset[str] = frozenset({"en", "el", "es", "pt", "cs", "de", "it", "fi", "nb", "bg", "pl"})

# Labels for the language dropdown (native names)
LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "el": "Ελληνικά",
    "es": "Español",
    "pt": "Português",
    "cs": "Čeština",
    "de": "Deutsch",
    "it": "Italiano",
    "fi": "Suomi",
    "nb": "Norsk",
    "bg": "Български",
    "pl": "Polski",
}

# Flag country codes for flag-icons CSS (language → ISO 3166-1 alpha-2)
LANGUAGE_FLAGS: dict[str, str] = {
    "en": "gb",
    "el": "gr",
    "es": "es",
    "pt": "pt",
    "cs": "cz",
    "de": "at",
    "it": "it",
    "fi": "fi",
    "nb": "no",
    "bg": "bg",
    "pl": "pl",
}


def install_i18n(env: Environment) -> None:
    """Add the i18n extension and install passthrough translations."""
    env.add_extension("jinja2.ext.i18n")
    env.install_gettext_translations(gettext.NullTranslations())


@lru_cache(maxsize=8)
def get_translations(locale: str) -> gettext.NullTranslations:
    """Return compiled translations for the given locale.

    English and unknown locales get NullTranslations (passthrough).
    Non-English supported locales get GNUTranslations from .mo files.
    Falls back to NullTranslations if the .mo file is missing.
    """
    if locale == "en" or locale not in SUPPORTED_LOCALES:
        return gettext.NullTranslations()
    try:
        return gettext.translation(
            "messages",
            localedir=str(_TRANSLATIONS_DIR),
            languages=[locale],
        )
    except FileNotFoundError:
        return gettext.NullTranslations()
