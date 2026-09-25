from collections.abc import Sequence
from typing import Protocol

from app.core.i18n import DEFAULT_LOCALE, Locale


class HasLocale(Protocol):
    locale: Locale


def check_translations(translations: Sequence[HasLocale], *, require_default: bool) -> None:
    locales = [translation.locale for translation in translations]
    if len(locales) != len(set(locales)):
        raise ValueError("Chaque langue ne peut apparaître qu'une seule fois.")
    if require_default and DEFAULT_LOCALE not in locales:
        raise ValueError(f"La traduction « {DEFAULT_LOCALE.value} » est obligatoire.")
