"""Tests for inline event handler detection in templates.

Ensures no onclick, onchange, onsubmit, etc. exist in Jinja2 templates,
which would violate the nonce-based CSP policy.
"""

import re
from pathlib import Path

import pytest

# Pattern matching inline event handlers in HTML attributes
INLINE_HANDLER_PATTERN = re.compile(
    r'\bon(click|change|submit|load|error|input|focus|blur|keydown|keyup'
    r'|keypress|mouseover|mouseout|mousedown|mouseup|resize|scroll)\s*=',
    re.IGNORECASE,
)

TEMPLATES_DIR = Path("app/templates")


def _scan_templates_for_inline_handlers() -> list[tuple[str, int, str]]:
    """Scan all templates and return (file, line_no, line) for violations."""
    violations: list[tuple[str, int, str]] = []
    for template in TEMPLATES_DIR.rglob("*.html"):
        for i, line in enumerate(template.read_text().splitlines(), start=1):
            if INLINE_HANDLER_PATTERN.search(line):
                violations.append((str(template), i, line.strip()))
    return violations


class TestNoInlineHandlersInTemplates:
    """All templates must be free of inline event handlers (CSP compliance)."""

    def test_no_inline_handlers_in_any_template(self) -> None:
        violations = _scan_templates_for_inline_handlers()
        if violations:
            report = "\n".join(
                f"  {f}:{ln}: {text}" for f, ln, text in violations
            )
            pytest.fail(
                f"Inline event handlers violate CSP. Found {len(violations)}:\n{report}"
            )

    def test_pattern_catches_onclick(self) -> None:
        assert INLINE_HANDLER_PATTERN.search('onclick="doStuff()"')

    def test_pattern_catches_onchange(self) -> None:
        assert INLINE_HANDLER_PATTERN.search("onchange='update()'")

    def test_pattern_catches_onsubmit(self) -> None:
        assert INLINE_HANDLER_PATTERN.search('onsubmit="return false"')

    def test_pattern_ignores_non_handler_attributes(self) -> None:
        assert not INLINE_HANDLER_PATTERN.search('class="button"')
        assert not INLINE_HANDLER_PATTERN.search('data-on="click"')

    def test_pattern_case_insensitive(self) -> None:
        assert INLINE_HANDLER_PATTERN.search('onClick="x()"')
        assert INLINE_HANDLER_PATTERN.search('ONCLICK="x()"')
