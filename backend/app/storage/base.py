from typing import Protocol


class Storage(Protocol):
    """Contrat de stockage des fichiers : disque local aujourd'hui, stockage objet demain."""

    async def save(self, key: str, content: bytes) -> None: ...

    async def delete(self, key: str) -> None: ...

    def url(self, key: str) -> str: ...
