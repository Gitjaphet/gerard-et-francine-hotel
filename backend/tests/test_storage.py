from pathlib import Path

import pytest

from app.storage.local import LocalStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path, "/media/")


async def test_save_writes_file_in_nested_folders(storage: LocalStorage, tmp_path: Path) -> None:
    await storage.save("rooms/abc/md.webp", b"image-bytes")

    assert (tmp_path / "rooms/abc/md.webp").read_bytes() == b"image-bytes"


async def test_delete_removes_file_and_ignores_missing_ones(
    storage: LocalStorage, tmp_path: Path
) -> None:
    await storage.save("a.webp", b"x")

    await storage.delete("a.webp")
    await storage.delete("a.webp")

    assert not (tmp_path / "a.webp").exists()


def test_url_joins_base_url_and_key(storage: LocalStorage) -> None:
    assert storage.url("rooms/abc/md.webp") == "/media/rooms/abc/md.webp"


@pytest.mark.parametrize("key", ["../outside.webp", "rooms/../../etc/passwd", "/etc/passwd"])
async def test_keys_escaping_the_storage_root_are_rejected(storage: LocalStorage, key: str) -> None:
    with pytest.raises(ValueError, match="invalide"):
        await storage.save(key, b"x")
