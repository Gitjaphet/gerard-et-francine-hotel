from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.i18n import Locale
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, locale_check

room_type_amenity = Table(
    "room_type_amenity",
    Base.metadata,
    Column("room_type_id", ForeignKey("room_type.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenity.id", ondelete="CASCADE"), primary_key=True),
)


# --- Équipements -------------------------------------------------------------


class Amenity(TimestampMixin, Base):
    __tablename__ = "amenity"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    icon: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(default=0)

    translations: Mapped[list["AmenityTranslation"]] = relationship(
        back_populates="amenity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AmenityTranslation(TimestampMixin, Base):
    __tablename__ = "amenity_translation"
    __table_args__ = (UniqueConstraint("amenity_id", "locale"), locale_check())

    id: Mapped[int] = mapped_column(primary_key=True)
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenity.id", ondelete="CASCADE"))
    locale: Mapped[Locale] = mapped_column(LocaleType)
    name: Mapped[str] = mapped_column(String(100))

    amenity: Mapped[Amenity] = relationship(back_populates="translations")


# --- Types de chambres -------------------------------------------------------


class RoomType(TimestampMixin, Base):
    __tablename__ = "room_type"
    __table_args__ = (
        CheckConstraint("max_adults >= 1", name="max_adults_positive"),
        CheckConstraint("max_children >= 0", name="max_children_not_negative"),
        CheckConstraint("units_count >= 1", name="units_count_positive"),
        CheckConstraint("size_m2 IS NULL OR size_m2 > 0", name="size_m2_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    max_adults: Mapped[int] = mapped_column(SmallInteger, default=2)
    max_children: Mapped[int] = mapped_column(SmallInteger, default=0)
    size_m2: Mapped[int | None] = mapped_column(SmallInteger)
    units_count: Mapped[int] = mapped_column(SmallInteger, default=1)
    position: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=False)

    translations: Mapped[list["RoomTypeTranslation"]] = relationship(
        back_populates="room_type",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    amenities: Mapped[list[Amenity]] = relationship(
        secondary=room_type_amenity,
        order_by=Amenity.position,
        lazy="selectin",
    )


class RoomTypeTranslation(TimestampMixin, Base):
    __tablename__ = "room_type_translation"
    __table_args__ = (
        UniqueConstraint("room_type_id", "locale"),
        UniqueConstraint("locale", "slug"),
        locale_check(),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_type.id", ondelete="CASCADE"))
    locale: Mapped[Locale] = mapped_column(LocaleType)

    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(160))
    short_description: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    bed_description: Mapped[str | None] = mapped_column(String(150))
    meta_title: Mapped[str | None] = mapped_column(String(70))
    meta_description: Mapped[str | None] = mapped_column(String(160))

    room_type: Mapped[RoomType] = relationship(back_populates="translations")
