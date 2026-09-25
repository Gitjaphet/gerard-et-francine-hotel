from collections.abc import Callable, Sequence
from typing import Any, Protocol

from app.core.i18n import Locale


class LocalizedRow(Protocol):
    @property
    def locale(self) -> Locale: ...


class LocalizedInput(Protocol):
    @property
    def locale(self) -> Locale: ...

    def model_dump(self, *, exclude: set[str]) -> dict[str, Any]: ...


def sync_translations[T: LocalizedRow](
    rows: list[T],
    items: Sequence[LocalizedInput],
    build: Callable[..., T],
) -> None:
    """Met à jour les traductions existantes et crée les nouvelles.

    Une langue absente de `items` est conservée : un formulaire incomplet
    ne doit jamais effacer une traduction.
    """
    existing = {row.locale: row for row in rows}
    for item in items:
        values = item.model_dump(exclude={"locale"})
        current = existing.get(item.locale)
        if current is None:
            rows.append(build(locale=item.locale, **values))
        else:
            for name, value in values.items():
                setattr(current, name, value)
