"""Tests for translation files."""
from pathlib import Path

import pytest

TRANSLATIONS_DIR = Path("app/translations")
EL_PO_PATH = TRANSLATIONS_DIR / "el" / "LC_MESSAGES" / "messages.po"
EL_MO_PATH = TRANSLATIONS_DIR / "el" / "LC_MESSAGES" / "messages.mo"


def test_el_translation_file_exists() -> None:
    """Verify Greek .po file exists."""
    assert EL_PO_PATH.exists(), f"Greek .po file not found at {EL_PO_PATH}"


def test_el_translation_compiled_mo_exists() -> None:
    """Verify compiled Greek .mo file exists."""
    assert EL_MO_PATH.exists(), f"Compiled .mo file not found at {EL_MO_PATH}"


def test_el_translation_no_empty_msgstr() -> None:
    """Every msgid (except the header) must have a non-empty msgstr."""
    content = EL_PO_PATH.read_text(encoding="utf-8")
    in_header = True
    msgid = ""

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("msgid "):
            msgid = line[7:-1]  # strip msgid " and trailing "
            if msgid:  # non-empty msgid means we're past the header
                in_header = False
        elif line.startswith("msgstr ") and not in_header:
            msgstr = line[8:-1]  # strip msgstr " and trailing "
            if msgid and not msgstr:
                pytest.fail(f"Empty msgstr for msgid: {msgid!r}")
