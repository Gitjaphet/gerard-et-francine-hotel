from datetime import time
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.i18n import Locale
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, locale_check


class HotelSettings(TimestampMixin, Base):
    __tablename__ = "hotel_settings"
    __table_args__ = (CheckConstraint("stars BETWEEN 1 AND 5", name="stars_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    stars: Mapped[int | None] = mapped_column(SmallInteger)

    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    whatsapp: Mapped[str | None] = mapped_column(String(30))

    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Madagascar")
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    google_maps_url: Mapped[str | None] = mapped_column(String(500))
    google_place_id: Mapped[str | None] = mapped_column(String(255))

    check_in_time: Mapped[time] = mapped_column(default=time(14, 0))
    check_out_time: Mapped[time] = mapped_column(default=time(11, 0))

    eur_to_mga_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    show_mga_prices: Mapped[bool] = mapped_column(default=False)

    nif: Mapped[str | None] = mapped_column(String(50))
    stat: Mapped[str | None] = mapped_column(String(50))

    translations: Mapped[list["HotelSettingsTranslation"]] = relationship(
        back_populates="settings",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class HotelSettingsTranslation(TimestampMixin, Base):
    __tablename__ = "hotel_settings_translation"
    __table_args__ = (UniqueConstraint("settings_id", "locale"), locale_check())

    id: Mapped[int] = mapped_column(primary_key=True)
    settings_id: Mapped[int] = mapped_column(
        ForeignKey("hotel_settings.id", ondelete="CASCADE"),
        index=True,
    )
    locale: Mapped[Locale] = mapped_column(LocaleType)

    tagline: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    meta_title: Mapped[str | None] = mapped_column(String(70))
    meta_description: Mapped[str | None] = mapped_column(String(160))

    settings: Mapped[HotelSettings] = relationship(back_populates="translations")


class SocialLink(TimestampMixin, Base):
    __tablename__ = "social_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
