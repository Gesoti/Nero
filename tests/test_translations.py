"""Tests for translation infrastructure — multi-language support.

The app supports English (default) and Greek. Translations are stored
as Babel .po/.mo files in app/translations/{locale}/LC_MESSAGES/.
"""
from pathlib import Path


def test_translations_directory_exists() -> None:
    """The app/translations directory must exist with at least Greek."""
    translations_dir = Path("app/translations")
    assert translations_dir.exists()


def test_greek_mo_file_exists() -> None:
    """Compiled Greek .mo file must exist for runtime translations."""
    mo_path = Path("app/translations/el/LC_MESSAGES/messages.mo")
    assert mo_path.exists(), "Greek .mo file not found — run: uv run pybabel compile -d app/translations"


def test_greek_po_file_has_translations() -> None:
    """Greek .po file must have non-empty msgstr entries."""
    po_path = Path("app/translations/el/LC_MESSAGES/messages.po")
    content = po_path.read_text(encoding="utf-8")
    # Count non-empty msgstr (excluding the header metadata msgstr)
    lines = content.split("\n")
    filled = sum(
        1 for i, line in enumerate(lines)
        if line.startswith('msgstr "') and line != 'msgstr ""' and i > 18
    )
    assert filled >= 20, f"Expected at least 20 translated strings, found {filled}"
