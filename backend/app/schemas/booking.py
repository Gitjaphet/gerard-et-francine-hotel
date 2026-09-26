from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.booking import BookingStatus, BookingWarning
from app.core.i18n import DEFAULT_LOCALE, Locale


class BookingRequestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    room_type_id: int
    check_in: date
    check_out: date
    adults: int = Field(ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    children_ages: list[int] = Field(default=[], max_length=20)

    guest_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ().-]{6,30}$")
    prefers_whatsapp: bool = False
    locale: Locale = DEFAULT_LOCALE
    message: str | None = Field(default=None, max_length=2000)

    # Piège à robots : champ caché dans le formulaire, qu'un humain laisse toujours vide.
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        if self.check_out <= self.check_in:
            raise ValueError("La date de départ doit être postérieure à la date d'arrivée.")
        if self.children_ages and len(self.children_ages) != self.children:
            raise ValueError("Indiquez l'âge de chaque enfant.")
        if any(age < 0 or age > 17 for age in self.children_ages):
            raise ValueError("L'âge d'un enfant doit être compris entre 0 et 17 ans.")
        if self.prefers_whatsapp and not self.phone:
            raise ValueError(
                "Un numéro de téléphone est nécessaire pour être contacté sur WhatsApp."
            )
        return self


class BookingRequestReceipt(BaseModel):
    """Ce que voit le client juste après l'envoi : jamais les données internes."""

    reference: str
    status: BookingStatus
    check_in: date
    check_out: date
    nights_count: int
    quoted_total: Decimal | None
    currency: str = "EUR"
    min_nights_required: int | None
    warnings: list[BookingWarning]
