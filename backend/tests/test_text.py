import pytest

from app.core.text import slugify


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Bungalow Vue Mer", "bungalow-vue-mer"),
        ("Chambre créole à l'étage", "chambre-creole-a-l-etage"),
        ("Große Suite mit Meerblick", "grosse-suite-mit-meerblick"),
        ("Camera con vista sul giardino", "camera-con-vista-sul-giardino"),
        ("Le cœur de Nosy Be", "le-coeur-de-nosy-be"),
        ("  --Double   espace!!  ", "double-espace"),
        ("Suite N°2 (2 personnes)", "suite-n-2-2-personnes"),
        ("Chambre à l\u2019étage", "chambre-a-l-etage"),
        ("Bungalow \u2013 Vue mer", "bungalow-vue-mer"),
    ],
)
def test_slugify_handles_all_supported_languages(value: str, expected: str) -> None:
    assert slugify(value) == expected


def test_slugify_respects_max_length_without_trailing_dash() -> None:
    slug = slugify("aaaa bbbb", max_length=5)

    assert slug == "aaaa"


def test_slugify_returns_empty_string_when_nothing_is_usable() -> None:
    assert slugify("!!! ???") == ""
