from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    return LocalStorage(settings.media_root, settings.media_url)
