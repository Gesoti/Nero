"""
Tests for the centralised dam description registry.

The registry maps country code → description dict, enabling a single
dispatch call instead of a 13-branch if/elif chain in pages.py.
"""
import pytest
from app.dam_description_registry import DESCRIPTION_REGISTRY, get_description


# --------------------------------------------------------------------------- #
# Registry completeness
# --------------------------------------------------------------------------- #

EXPECTED_COUNTRIES = ["cy", "gr", "es", "pt", "cz", "at", "it", "fi", "no", "ch", "bg", "de", "pl"]


@pytest.mark.parametrize("cc", EXPECTED_COUNTRIES)
def test_registry_contains_all_countries(cc: str) -> None:
    assert cc in DESCRIPTION_REGISTRY, f"Country '{cc}' missing from DESCRIPTION_REGISTRY"


def test_registry_has_exactly_expected_countries() -> None:
    assert set(DESCRIPTION_REGISTRY.keys()) == set(EXPECTED_COUNTRIES)


# --------------------------------------------------------------------------- #
# get_description behaviour
# --------------------------------------------------------------------------- #

def test_get_description_known_country_known_dam() -> None:
    result = get_description("gr", "Mornos")
    assert isinstance(result, str)
    assert len(result) > 100


def test_get_description_known_country_unknown_dam_returns_str() -> None:
    # Unknown dam must return a str (empty or fallback), never raise
    result = get_description("gr", "NonExistentDam")
    assert isinstance(result, str)


def test_get_description_unknown_country_returns_empty_string() -> None:
    result = get_description("xx", "SomeDam")
    assert result == ""


def test_get_description_cy_known_dam() -> None:
    """Cyprus is the default country (no prefix); ensure it resolves correctly."""
    result = get_description("cy", "Kouris")
    assert isinstance(result, str)
    assert len(result) > 100


def test_get_description_no_zone() -> None:
    result = get_description("no", "NO1-East")
    assert isinstance(result, str)
    assert len(result) > 50


def test_get_description_ch_region() -> None:
    result = get_description("ch", "NonExistentRegion")
    assert isinstance(result, str)  # ch has a fallback
