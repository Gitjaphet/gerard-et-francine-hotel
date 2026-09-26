from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.booking import BookingStatus
from app.core.i18n import Locale
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, enum_check, locale_check, string_enum


class BookingRequest(TimestampMixin, Base):
    __tablename__ = "booking_request"
    __table_args__ = (
        CheckConstraint("check_out > check_in", name="dates_in_order"),
        CheckConstraint("adults >= 1", name="adults_positive"),
        CheckConstraint("children >= 0", name="children_not_negative"),
        enum_check("status", BookingStatus),
        locale_check(),
        Index("ix_booking_request_status_created_at", "status", "created_at"),
        Index("ix_booking_request_check_in", "check_in"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(
        String(20),
        Computed("'GF-' || lpad(id::text, 5, '0')", persisted=True),
        unique=True,
    )
    status: Mapped[BookingStatus] = mapped_column(
        string_enum(BookingStatus, name="booking_status", length=20),
        default=BookingStatus.PENDING,
    )

    # Séjour demandé
    room_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_type.id", ondelete="SET NULL"), index=True
    )
    room_name: Mapped[str] = mapped_column(String(150))
    check_in: Mapped[date]
    check_out: Mapped[date]
    adults: Mapped[int] = mapped_column(SmallInteger)
    children: Mapped[int] = mapped_column(SmallInteger, default=0)
    children_ages: Mapped[list[int]] = mapped_column(JSONB, default=list)

    # Prix indicatif, figé au moment de la demande
    nights_count: Mapped[int] = mapped_column(SmallInteger)
    quoted_total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Client
    guest_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    prefers_whatsapp: Mapped[bool] = mapped_column(default=False)
    locale: Mapped[Locale] = mapped_column(LocaleType)
    message: Mapped[str | None] = mapped_column(Text)

    # Traitement par la réception
    staff_notes: Mapped[str | None] = mapped_column(Text)
    handled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_user.id", ondelete="SET NULL")
    )
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
