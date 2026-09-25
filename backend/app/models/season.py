from datetime import date

from sqlalchemy import CheckConstraint, Computed, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.i18n import Locale
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, locale_check


class Season(TimestampMixin, Base):
    __tablename__ = "season"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates_in_order"),
        CheckConstraint("min_nights IS NULL OR min_nights >= 1", name="min_nights_positive"),
        ExcludeConstraint(("period", "&&"), name="ex_season_no_overlap", using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date]
    end_date: Mapped[date]
    period: Mapped[Range[date]] = mapped_column(
        DATERANGE,
        Computed("daterange(start_date, end_date, '[]')", persisted=True),
    )
    min_nights: Mapped[int | None] = mapped_column(SmallInteger)

    translations: Mapped[list["SeasonTranslation"]] = relationship(
        back_populates="season",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SeasonTranslation(TimestampMixin, Base):
    __tablename__ = "season_translation"
    __table_args__ = (UniqueConstraint("season_id", "locale"), locale_check())

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("season.id", ondelete="CASCADE"))
    locale: Mapped[Locale] = mapped_column(LocaleType)
    name: Mapped[str] = mapped_column(String(100))

    season: Mapped[Season] = relationship(back_populates="translations")
