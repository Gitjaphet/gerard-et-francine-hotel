from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.i18n import Locale
from app.core.text import slugify
from app.schemas.common import check_translations

# --- Équipements -------------------------------------------------------------


class AmenityTranslationWrite(BaseModel):
    locale: Locale
    name: str = Field(min_length=1, max_length=100)


class AmenityTranslationRead(AmenityTranslationWrite):
    model_config = ConfigDict(from_attributes=True)


class AmenityFields(BaseModel):
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    icon: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    position: int = Field(default=0, ge=0)


class AmenityWrite(AmenityFields):
    translations: list[AmenityTranslationWrite] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_translations(self) -> Self:
        check_translations(self.translations, require_default=True)
        return self


class AmenityRead(AmenityFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    translations: list[AmenityTranslationRead]


# --- Types de chambres -------------------------------------------------------


class RoomTypeTextFields(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    bed_description: str | None = Field(default=None, max_length=150)
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class RoomTypeTranslationWrite(RoomTypeTextFields):
    locale: Locale
    slug: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def build_slug(self) -> Self:
        self.slug = slugify(self.slug or self.name)
        if not self.slug:
            raise ValueError("Impossible de générer une adresse de page à partir de ce nom.")
        return self


class RoomTypeTranslationRead(RoomTypeTextFields):
    model_config = ConfigDict(from_attributes=True)

    locale: Locale
    slug: str


class RoomTypeFields(BaseModel):
    max_adults: int = Field(default=2, ge=1, le=20)
    max_children: int = Field(default=0, ge=0, le=20)
    size_m2: int | None = Field(default=None, gt=0, le=1000)
    units_count: int = Field(default=1, ge=1, le=100)
    position: int = Field(default=0, ge=0)
    is_active: bool = False


class RoomTypeWrite(RoomTypeFields):
    amenity_ids: list[int] = []
    translations: list[RoomTypeTranslationWrite] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        check_translations(self.translations, require_default=True)
        self.amenity_ids = list(dict.fromkeys(self.amenity_ids))
        return self


class RoomTypeRead(RoomTypeFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    translations: list[RoomTypeTranslationRead]
    amenities: list[AmenityRead]
    updated_at: datetime


# --- Vue publique ------------------------------------------------------------


class AmenityPublic(BaseModel):
    code: str
    icon: str
    name: str


class RoomTypePublic(RoomTypeTextFields):
    id: int
    slug: str
    locale: Locale
    content_locale: Locale
    slugs: dict[Locale, str]
    max_adults: int
    max_children: int
    size_m2: int | None
    amenities: list[AmenityPublic]
