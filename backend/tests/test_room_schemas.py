import pytest
from pydantic import ValidationError

from app.schemas.room import AmenityWrite, RoomTypeTranslationWrite, RoomTypeWrite


def test_slug_is_generated_from_name_when_missing() -> None:
    translation = RoomTypeTranslationWrite(locale="fr", name="Bungalow Vue Mer")

    assert translation.slug == "bungalow-vue-mer"


def test_custom_slug_is_normalized() -> None:
    translation = RoomTypeTranslationWrite(locale="fr", name="Bungalow", slug="Ma Suite !")

    assert translation.slug == "ma-suite"


def test_name_without_usable_characters_is_rejected() -> None:
    with pytest.raises(ValidationError, match="adresse de page"):
        RoomTypeTranslationWrite(locale="fr", name="!!!")


def test_room_type_requires_french_translation() -> None:
    with pytest.raises(ValidationError, match="« fr » est obligatoire"):
        RoomTypeWrite(translations=[{"locale": "en", "name": "Sea view bungalow"}])


def test_room_type_rejects_duplicate_locales() -> None:
    with pytest.raises(ValidationError, match="une seule fois"):
        RoomTypeWrite(translations=[{"locale": "fr", "name": "A"}, {"locale": "fr", "name": "B"}])


def test_duplicate_amenity_ids_are_removed_keeping_order() -> None:
    room = RoomTypeWrite(amenity_ids=[3, 1, 3, 2, 1], translations=[{"locale": "fr", "name": "A"}])

    assert room.amenity_ids == [3, 1, 2]


@pytest.mark.parametrize("code", ["Fan", "1fan", "solar hot water", "x"])
def test_amenity_code_must_be_a_technical_identifier(code: str) -> None:
    with pytest.raises(ValidationError):
        AmenityWrite(code=code, icon="fan", translations=[{"locale": "fr", "name": "Ventilateur"}])
