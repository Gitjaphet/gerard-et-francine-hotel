from enum import StrEnum


class Locale(StrEnum):
    FR = "fr"
    EN = "en"
    IT = "it"
    DE = "de"


DEFAULT_LOCALE = Locale.FR
