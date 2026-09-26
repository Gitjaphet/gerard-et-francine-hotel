from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.i18n import Locale
from app.core.review import ReviewStatus
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, enum_check, locale_check, string_enum


class Review(TimestampMixin, Base):
    __tablename__ = "review"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        enum_check("status", ReviewStatus),
        locale_check(),
        Index("ix_review_status_created_at", "status", "created_at"),
        Index("ix_review_ip_hash_created_at", "ip_hash", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[ReviewStatus] = mapped_column(
        string_enum(ReviewStatus, name="review_status", length=20),
        default=ReviewStatus.PENDING,
    )

    # Contenu public
    author_name: Mapped[str] = mapped_column(String(100))
    author_country: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str | None] = mapped_column(String(150))
    body: Mapped[str] = mapped_column(Text)
    locale: Mapped[Locale] = mapped_column(LocaleType)
    stayed_on: Mapped[date | None]

    # Données internes, jamais publiées
    email: Mapped[str] = mapped_column(String(255))
    ip_hash: Mapped[str] = mapped_column(String(64))

    # Modération et réponse de l'hôtel
    owner_reply: Mapped[str | None] = mapped_column(Text)
    moderated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_user.id", ondelete="SET NULL")
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
