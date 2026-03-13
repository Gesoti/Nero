"""Tests for translation infrastructure — English-only mode.

Multilingual support was removed (all countries use English).
The i18n extension is kept for _() passthrough but no .po/.mo files are needed.
"""


def test_i18n_is_english_only() -> None:
    """Verify no non-English translation files exist."""
    from pathlib import Path

    translations_dir = Path("app/translations")
    if translations_dir.exists():
        locale_dirs = [d for d in translations_dir.iterdir() if d.is_dir()]
        assert len(locale_dirs) == 0, (
            f"Expected no locale directories (English-only mode), found: {[d.name for d in locale_dirs]}"
        )
