"""Tests for app/config.py — country and locale settings."""
from __future__ import annotations


class TestCountryLocaleConfig:
    def test_default_country_is_cy(self):
        from app.config import settings
        assert settings.country == "cy"

    def test_default_locale_is_en(self):
        from app.config import settings
        assert settings.locale == "en"

    def test_country_field_exists(self):
        from app.config import Settings
        assert "country" in Settings.model_fields

    def test_locale_field_exists(self):
        from app.config import Settings
        assert "locale" in Settings.model_fields


class TestDbPathFromCountry:
    def test_default_db_path_uses_country(self):
        """Default db_path should incorporate country code: data/{cc}/water.db"""
        from app.config import Settings
        s = Settings(country="cy")
        assert s.db_path == "data/cy/water.db"

    def test_greece_db_path(self):
        from app.config import Settings
        s = Settings(country="gr")
        assert s.db_path == "data/gr/water.db"

    def test_explicit_db_path_overrides(self):
        """If WL_DB_PATH is explicitly set, it should be used as-is."""
        from app.config import Settings
        s = Settings(country="cy", db_path="custom/path.db")
        assert s.db_path == "custom/path.db"
