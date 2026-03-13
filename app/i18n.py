"""
Internationalization setup — Babel + Jinja2 i18n extension.

Installs NullTranslations (passthrough) for the default English locale.
Future locales will load compiled .mo files from app/i18n/{cc}/{lang}/LC_MESSAGES/.
"""
from __future__ import annotations

import gettext

from jinja2 import Environment


def install_i18n(env: Environment) -> None:
    """Add the i18n extension and install passthrough translations."""
    env.add_extension("jinja2.ext.i18n")
    # NullTranslations returns msgid unchanged — perfect for English source strings
    env.install_gettext_translations(gettext.NullTranslations())
