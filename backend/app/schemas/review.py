from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.i18n import DEFAULT_LOCALE, Locale
from app.core.review import ReviewStatus


class ReviewCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    author_name: str = Field(min_length=2, max_length=100)
    author_country: str | None = Field(default=None, max_length=100)
    email: EmailStr
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=150)
    body: str = Field(min_length=20, max_length=3000)
    locale: Locale = DEFAULT_LOCALE
    stayed_on: date | None = None

    # Piège à robots, comme pour les demandes de réservation.
    website: str = Field(default="", max_length=200)


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_name: str
    author_country: str | None
    rating: int
    title: str | None
    body: str
    locale: Locale
    stayed_on: date | None
    owner_reply: str | None
    created_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewPublic]
    total: int
    page: int
    page_size: int


class ReviewSummary(BaseModel):
    count: int
    average: Decimal | None
    distribution: dict[int, int]


class ReviewReceipt(BaseModel):
    """Réponse au dépôt : l'avis attend la modération, il n'est pas encore visible."""

    status: str = "pending"


# --- Modération (admin) -------------------------------------------------------------


class ReviewAdminRead(ReviewPublic):
    status: ReviewStatus
    email: str
    moderated_by_id: int | None
    moderated_at: datetime | None


class ReviewModeration(BaseModel):
    status: Literal[ReviewStatus.APPROVED, ReviewStatus.REJECTED]


class ReviewReply(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    owner_reply: str | None = Field(default=None, max_length=2000)
