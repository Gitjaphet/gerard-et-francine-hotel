from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.i18n import Locale
from app.schemas.common import check_translations


class MediaTranslationWrite(BaseModel):
    locale: Locale
    alt_text: str = Field(min_length=1, max_length=255)


class MediaTranslationRead(MediaTranslationWrite):
    model_config = ConfigDict(from_attributes=True)


class MediaTranslationsUpdate(BaseModel):
    translations: list[MediaTranslationWrite]

    @model_validator(mode="after")
    def validate_translations(self) -> Self:
        check_translations(self.translations, require_default=False)
        return self


class MediaVariantRead(BaseModel):
    url: str
    width: int
    height: int


class MediaAssetRead(BaseModel):
    id: int
    original_filename: str
    width: int
    height: int
    variants: dict[str, MediaVariantRead]
    translations: list[MediaTranslationRead]
