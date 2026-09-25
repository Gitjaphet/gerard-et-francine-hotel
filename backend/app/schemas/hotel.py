from datetime import datetime, time
from enum import StrEnum
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.i18n import Locale

# --- Traductions -------------------------------------------------------------


class HotelTranslationFields(BaseModel):
    tagline: str | None = Field(default=None, max_length=255)
    description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class HotelSettingsTranslationWrite(HotelTranslationFields):
    locale: Locale


class HotelSettingsTranslationRead(HotelTranslationFields):
    model_config = ConfigDict(from_attributes=True)

    locale: Locale


# --- Réglages de l'hôtel -----------------------------------------------------


class HotelSettingsFields(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    stars: int | None = Field(default=None, ge=1, le=5)

    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    whatsapp: str | None = Field(default=None, pattern=r"^\+[1-9]\d{6,14}$")

    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    country: str = Field(default="Madagascar", max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=6)
    google_maps_url: str | None = Field(default=None, max_length=500, pattern=r"^https://")
    google_place_id: str | None = Field(default=None, max_length=255)

    check_in_time: time = time(14, 0)
    check_out_time: time = time(11, 0)

    eur_to_mga_rate: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    show_mga_prices: bool = False

    nif: str | None = Field(default=None, max_length=50)
    stat: str | None = Field(default=None, max_length=50)


class HotelSettingsUpdate(HotelSettingsFields):
    translations: list[HotelSettingsTranslationWrite] = []

    @model_validator(mode="after")
    def check_translations(self) -> "HotelSettingsUpdate":
        locales = [t.locale for t in self.translations]
        if len(locales) != len(set(locales)):
            raise ValueError("Chaque langue ne peut apparaître qu'une seule fois.")
        if self.show_mga_prices and self.eur_to_mga_rate is None:
            raise ValueError("Un taux EUR→MGA est requis pour afficher les prix en ariary.")
        return self


class HotelSettingsRead(HotelSettingsFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    translations: list[HotelSettingsTranslationRead]
    updated_at: datetime


# --- Réseaux sociaux ---------------------------------------------------------


class SocialPlatform(StrEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TRIPADVISOR = "tripadvisor"
    BOOKING = "booking"
    GOOGLE = "google"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    X = "x"
    LINKEDIN = "linkedin"


class SocialLinkWrite(BaseModel):
    platform: SocialPlatform
    url: str = Field(max_length=500, pattern=r"^https://")
    position: int = Field(default=0, ge=0)
    is_active: bool = True


class SocialLinkRead(SocialLinkWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- Vue publique (site) -----------------------------------------------------


class SocialLinkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: SocialPlatform
    url: str


class HotelPublicInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    stars: int | None
    email: str
    phone: str | None
    whatsapp: str | None
    address: str | None
    city: str | None
    country: str
    latitude: Decimal | None
    longitude: Decimal | None
    google_maps_url: str | None
    check_in_time: time
    check_out_time: time


class HotelPublic(HotelPublicInfo, HotelTranslationFields):
    locale: Locale
    content_locale: Locale
    available_locales: list[Locale]
    mga_rate: Decimal | None
    social_links: list[SocialLinkPublic]
