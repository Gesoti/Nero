"""Tests for i18n integration — multi-language support via Babel."""
from __future__ import annotations

import gettext


class TestI18nSetup:
    def test_jinja_env_has_i18n_extension(self):
        """The Jinja2 environment must have the i18n extension loaded."""
        from app.routes.pages import templates
        env = templates.env
        assert "jinja2.ext.InternationalizationExtension" in env.extensions

    def test_gettext_function_available_in_templates(self):
        """_() must be callable in the Jinja2 environment."""
        from app.routes.pages import templates
        env = templates.env
        assert "_" in env.globals or hasattr(env, "install_gettext_translations")

    def test_passthrough_translation_english(self):
        """With English locale, _() returns the input unchanged."""
        from app.routes.pages import templates
        from app.i18n import get_translations
        templates.env.install_gettext_translations(get_translations("en"))
        tmpl = templates.env.from_string("{{ _('Hello World') }}")
        result = tmpl.render()
        assert result == "Hello World"


class TestI18nMultiLanguage:
    """Translation loading for supported locales."""

    def test_get_translations_returns_null_for_en(self):
        from app.i18n import get_translations
        result = get_translations("en")
        assert isinstance(result, gettext.NullTranslations)

    def test_get_translations_returns_gnu_for_el(self):
        """Greek locale must return a real GNUTranslations object."""
        from app.i18n import get_translations
        result = get_translations("el")
        assert isinstance(result, gettext.GNUTranslations)

    def test_get_translations_fallback_for_unknown_locale(self):
        """Unknown locales must fall back to NullTranslations (English)."""
        from app.i18n import get_translations
        result = get_translations("xx")
        assert isinstance(result, gettext.NullTranslations)

    def test_get_translations_caches_result(self):
        """Repeated calls for the same locale must return the same object."""
        from app.i18n import get_translations
        t1 = get_translations("el")
        t2 = get_translations("el")
        assert t1 is t2

    def test_supported_locales_contains_en_and_el(self):
        """SUPPORTED_LOCALES must include at least en and el."""
        from app.i18n import SUPPORTED_LOCALES
        assert "en" in SUPPORTED_LOCALES
        assert "el" in SUPPORTED_LOCALES

    def test_greek_translates_known_string(self):
        """Greek translations must translate a known msgid."""
        from app.i18n import get_translations
        trans = get_translations("el")
        # "Map" is a short, well-defined string in the nav
        result = trans.gettext("Map")
        assert result != "Map", f"Expected Greek translation for 'Map', got '{result}'"
        assert result == "Χάρτης"
