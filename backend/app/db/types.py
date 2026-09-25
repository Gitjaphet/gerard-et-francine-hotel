from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum

from app.core.i18n import Locale


def string_enum(enum: type[StrEnum], name: str, length: int) -> Enum:
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
    )


def enum_check(column: str, enum: type[StrEnum]) -> CheckConstraint:
    allowed = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({allowed})", name=column)


LocaleType = string_enum(Locale, name="locale", length=5)


def locale_check(column: str = "locale") -> CheckConstraint:
    return enum_check(column, Locale)
