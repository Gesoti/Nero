import pytest
from app.gr_dam_descriptions import GR_DAM_DESCRIPTIONS

EXPECTED_DAMS = ["Mornos", "Yliki", "Evinos", "Marathon"]


@pytest.mark.parametrize("dam_name", EXPECTED_DAMS)
def test_gr_dam_description_exists(dam_name: str) -> None:
    assert dam_name in GR_DAM_DESCRIPTIONS
    assert len(GR_DAM_DESCRIPTIONS[dam_name]) > 0


@pytest.mark.parametrize("dam_name", EXPECTED_DAMS)
def test_gr_dam_description_word_count(dam_name: str) -> None:
    word_count = len(GR_DAM_DESCRIPTIONS[dam_name].split())
    assert 250 <= word_count <= 350, f"{dam_name} has {word_count} words, expected 250-350"


def test_gr_dam_description_unknown_returns_none() -> None:
    assert GR_DAM_DESCRIPTIONS.get("NonExistent") is None


def test_gr_dam_descriptions_count() -> None:
    assert len(GR_DAM_DESCRIPTIONS) == 4
