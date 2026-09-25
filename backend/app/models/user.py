from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import UserRole
from app.db.base import Base
from app.db.mixins import TimestampMixin
from app.db.types import enum_check, string_enum


class User(TimestampMixin, Base):
    __tablename__ = "admin_user"
    __table_args__ = (enum_check("role", UserRole),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(string_enum(UserRole, name="role", length=20))
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
