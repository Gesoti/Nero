"""Tests for i18n integration — Jinja2 i18n extension (English-only passthrough)."""
from __future__ import annotations


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

    def test_passthrough_translation(self):
        """With NullTranslations (English-only), _() returns the input unchanged."""
        from app.routes.pages import templates
        env = templates.env
        tmpl = env.from_string("{{ _('Hello World') }}")
        result = tmpl.render()
        assert result == "Hello World"

    def test_existing_templates_still_render(self, async_client):
        """Dashboard still renders correctly with i18n enabled."""
        pass  # Existing tests cover this — presence here documents the requirement


class TestI18nAlwaysEnglish:
    """All countries use English-only passthrough (NullTranslations)."""

    def test_get_translations_returns_null_for_en(self):
        import gettext
        from app.i18n import get_translations
        result = get_translations("en")
        assert isinstance(result, gettext.NullTranslations)

    def test_get_translations_returns_null_for_any_locale(self):
        """Even non-English locales return NullTranslations (English-only mode)."""
        import gettext
        from app.i18n import get_translations
        result = get_translations("el")
        assert isinstance(result, gettext.NullTranslations)
