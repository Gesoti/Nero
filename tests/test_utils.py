"""Tests for app/utils.py — slugify utility."""
from __future__ import annotations


class TestSlugify:
    def test_importable(self):
        from app.utils import slugify
        assert callable(slugify)

    def test_simple_name(self):
        from app.utils import slugify
        assert slugify("Kouris") == "kouris"

    def test_multi_word(self):
        from app.utils import slugify
        assert slugify("Marathon Lake") == "marathon-lake"

    def test_already_slug(self):
        from app.utils import slugify
        assert slugify("kouris") == "kouris"

    def test_strips_whitespace(self):
        from app.utils import slugify
        assert slugify("  Kouris  ") == "kouris"

    def test_replaces_multiple_hyphens(self):
        from app.utils import slugify
        assert slugify("Agia  Marina") == "agia-marina"

    def test_removes_special_chars(self):
        from app.utils import slugify
        assert slugify("St. John's Dam") == "st-johns-dam"

    def test_greek_transliteration(self):
        """Greek names from the API come as English transliterations, not Greek chars."""
        from app.utils import slugify
        assert slugify("Asprokremmos") == "asprokremmos"

    def test_stable_idempotent(self):
        from app.utils import slugify
        name = "Mavrokolympos"
        assert slugify(slugify(name)) == slugify(name)

    def test_existing_cyprus_dams_are_stable(self):
        """All current Cyprus dam names produce URL-safe slugs matching the current name (lowered)."""
        from app.utils import slugify
        cyprus_dams = [
            "Kouris", "Asprokremmos", "Evretou", "Kannaviou", "Kalavasos",
            "Dipotamos", "Lefkara", "Germasogeia", "Polemidia", "Achna",
            "Argaka", "Mavrokolympos", "Pomos", "Kalopanagiotis", "Xyliatos",
            "Arminou", "Solea",
        ]
        for name in cyprus_dams:
            slug = slugify(name)
            assert slug == name.lower(), f"slugify({name!r}) = {slug!r}, expected {name.lower()!r}"
