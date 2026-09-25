import asyncio
from pathlib import Path


class LocalStorage:
    def __init__(self, root: Path, base_url: str) -> None:
        self.root = root.resolve()
        self.base_url = base_url.rstrip("/")

    async def save(self, key: str, content: bytes) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, content)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key}"

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"Clé de stockage invalide : {key!r}")
        return path
