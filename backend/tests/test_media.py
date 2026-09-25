from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.main import app
from app.storage.deps import get_storage
from app.storage.local import LocalStorage
from tests.test_images import make_image

MEDIA_URL = "/api/v1/admin/media"


@pytest.fixture
def media_root(tmp_path: Path) -> Iterator[Path]:
    storage = LocalStorage(tmp_path, "/media")
    app.dependency_overrides[get_storage] = lambda: storage
    yield tmp_path
    app.dependency_overrides.pop(get_storage, None)


def stored_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


async def upload(client: AsyncClient, content: bytes, name: str = "photo.jpg") -> dict[str, object]:
    response = await client.post(MEDIA_URL, files={"file": (name, content, "image/jpeg")})
    return {"status": response.status_code, "body": response.json()}


async def test_upload_stores_three_webp_variants(
    owner_client: AsyncClient, media_root: Path
) -> None:
    result = await upload(owner_client, make_image(2400, 1600))

    assert result["status"] == 201
    body = result["body"]
    assert isinstance(body, dict)
    assert set(body["variants"]) == {"sm", "md", "lg"}
    assert body["variants"]["md"]["url"].startswith("/media/images/")
    assert body["variants"]["md"]["url"].endswith("/md.webp")
    assert "storage_key" not in body
    assert len(stored_files(media_root)) == 3


async def test_invalid_file_is_rejected_without_writing_anything(
    owner_client: AsyncClient, media_root: Path
) -> None:
    result = await upload(owner_client, b"<?php system($_GET['cmd']); ?>", name="shell.php.jpg")

    assert result["status"] == 422
    assert stored_files(media_root) == []


async def test_file_above_size_limit_is_rejected(
    owner_client: AsyncClient, media_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)

    result = await upload(owner_client, b"x" * (1024 * 1024 + 10))

    assert result["status"] == 413
    assert stored_files(media_root) == []


async def test_files_are_removed_when_database_write_fails(
    owner_client: AsyncClient, media_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_commit(self: AsyncSession) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    with pytest.raises(RuntimeError, match="database unavailable"):
        await upload(owner_client, make_image(1200, 800))

    assert stored_files(media_root) == []


async def test_alt_texts_can_be_translated(owner_client: AsyncClient, media_root: Path) -> None:
    body = (await upload(owner_client, make_image(1200, 800)))["body"]
    assert isinstance(body, dict)

    response = await owner_client.put(
        f"{MEDIA_URL}/{body['id']}/translations",
        json={"translations": [{"locale": "fr", "alt_text": "Bungalow face au lagon"}]},
    )

    assert response.status_code == 200
    assert response.json()["translations"] == [
        {"locale": "fr", "alt_text": "Bungalow face au lagon"}
    ]


async def test_delete_removes_database_row_and_files(
    owner_client: AsyncClient, media_root: Path
) -> None:
    body = (await upload(owner_client, make_image(1200, 800)))["body"]
    assert isinstance(body, dict)

    response = await owner_client.delete(f"{MEDIA_URL}/{body['id']}")

    assert response.status_code == 204
    assert stored_files(media_root) == []
    assert (await owner_client.delete(f"{MEDIA_URL}/{body['id']}")).status_code == 404


async def test_media_admin_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(MEDIA_URL, files={"file": ("a.jpg", b"x", "image/jpeg")})

    assert response.status_code == 401
