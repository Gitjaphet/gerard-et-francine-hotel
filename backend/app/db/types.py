from sqlalchemy import CheckConstraint, Enum

from app.core.i18n import Locale

LocaleType = Enum(
    Locale,
    name="locale",
    native_enum=False,
    create_constraint=False,
    length=5,
    values_callable=lambda enum: [member.value for member in enum],
)


def locale_check(column: str = "locale") -> CheckConstraint:
    allowed = ", ".join(f"'{locale.value}'" for locale in Locale)
    return CheckConstraint(f"{column} IN ({allowed})", name=column)
