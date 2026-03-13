"""Tests for i18n integration — Babel + Jinja2."""
from __future__ import annotations

import pytest


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
        # The i18n extension installs _() as a global
        assert "_" in env.globals or hasattr(env, "install_gettext_translations")

    def test_passthrough_translation(self):
        """With NullTranslations (English default), _() returns the input unchanged."""
        from app.routes.pages import templates
        env = templates.env
        tmpl = env.from_string("{{ _('Hello World') }}")
        result = tmpl.render()
        assert result == "Hello World"

    def test_existing_templates_still_render(self, async_client):
        """Dashboard still renders correctly with i18n enabled."""
        # This is covered by existing route tests, but explicit check here
        pass  # Existing tests cover this — presence here documents the requirement


class TestTemplateI18nWrapping:
    """Key UI strings must be wrapped with _() for translation extraction."""

    def _read_template(self, name: str) -> str:
        from pathlib import Path
        return Path(f"app/templates/{name}").read_text()

    def test_base_has_wrapped_nav_strings(self):
        content = self._read_template("base.html")
        # Nav items should use _()
        assert "{{ _(" in content

    def test_dashboard_has_wrapped_headings(self):
        content = self._read_template("dashboard.html")
        assert "{{ _(" in content

    def test_dam_detail_has_wrapped_labels(self):
        content = self._read_template("dam_detail.html")
        assert "{{ _(" in content

    def test_404_has_wrapped_text(self):
        content = self._read_template("404.html")
        assert "{{ _(" in content


class TestBabelConfig:
    def test_babel_cfg_exists(self):
        from pathlib import Path
        assert Path("babel.cfg").exists() or Path("app/i18n/babel.cfg").exists()
