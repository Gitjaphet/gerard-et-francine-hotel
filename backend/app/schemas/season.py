from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.i18n import Locale
from app.schemas.common import check_translations


class SeasonTranslationWrite(BaseModel):
    locale: Locale
    name: str = Field(min_length=1, max_length=100)


class SeasonTranslationRead(SeasonTranslationWrite):
    model_config = ConfigDict(from_attributes=True)


class SeasonRateWrite(BaseModel):
    room_type_id: int
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class SeasonRateRead(SeasonRateWrite):
    model_config = ConfigDict(from_attributes=True)


class SeasonFields(BaseModel):
    start_date: date
    end_date: date
    min_nights: int | None = Field(default=None, ge=1, le=60)


class SeasonWrite(SeasonFields):
    rates: list[SeasonRateWrite] = []
    translations: list[SeasonTranslationWrite] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("La date de fin doit être égale ou postérieure à la date de début.")
        check_translations(self.translations, require_default=True)
        room_type_ids = [rate.room_type_id for rate in self.rates]
        if len(room_type_ids) != len(set(room_type_ids)):
            raise ValueError("Une chambre ne peut avoir qu'un seul prix par saison.")
        return self


class SeasonRead(SeasonFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rates: list[SeasonRateRead]
    translations: list[SeasonTranslationRead]
