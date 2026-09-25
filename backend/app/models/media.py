from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.i18n import Locale
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import LocaleType, locale_check


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_asset"

    id: Mapped[int] = mapped_column(primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    width: Mapped[int]
    height: Mapped[int]
    variants: Mapped[dict[str, dict[str, int]]] = mapped_column(JSONB)

    translations: Mapped[list["MediaAssetTranslation"]] = relationship(
        back_populates="media_asset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MediaAssetTranslation(TimestampMixin, Base):
    __tablename__ = "media_asset_translation"
    __table_args__ = (UniqueConstraint("media_asset_id", "locale"), locale_check())

    id: Mapped[int] = mapped_column(primary_key=True)
    media_asset_id: Mapped[int] = mapped_column(ForeignKey("media_asset.id", ondelete="CASCADE"))
    locale: Mapped[Locale] = mapped_column(LocaleType)
    alt_text: Mapped[str] = mapped_column(String(255))

    media_asset: Mapped[MediaAsset] = relationship(back_populates="translations")
