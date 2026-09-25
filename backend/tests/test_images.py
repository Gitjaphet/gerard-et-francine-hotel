from io import BytesIO

import pytest
from PIL import Image

from app.core.images import InvalidImageError, process_image

GPS_INFO_TAG = 0x8825
ORIENTATION_TAG = 0x0112


def make_image(width: int, height: int, fmt: str = "JPEG", orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (width, height), color=(30, 120, 90))
    exif = image.getexif()
    exif[GPS_INFO_TAG] = {1: "S", 2: (13.0, 24.0, 1.8)}
    if orientation:
        exif[ORIENTATION_TAG] = orientation
    buffer = BytesIO()
    image.save(buffer, format=fmt, exif=exif.tobytes()) if fmt != "GIF" else image.save(buffer, fmt)
    return buffer.getvalue()


def test_large_photo_produces_three_webp_variants() -> None:
    result = process_image(make_image(3000, 2000))

    assert [(v.name, v.width) for v in result.variants] == [("sm", 400), ("md", 1200), ("lg", 2000)]
    assert all(Image.open(BytesIO(v.content)).format == "WEBP" for v in result.variants)


def test_images_are_never_upscaled() -> None:
    result = process_image(make_image(900, 600))

    assert [(v.name, v.width) for v in result.variants] == [("sm", 400), ("md", 900)]


def test_exif_metadata_including_gps_is_removed() -> None:
    result = process_image(make_image(1600, 1200))

    for variant in result.variants:
        assert not Image.open(BytesIO(variant.content)).getexif()


def test_exif_orientation_is_applied_before_stripping() -> None:
    result = process_image(make_image(1200, 900, orientation=6))

    assert (result.width, result.height) == (900, 1200)


def test_too_small_images_are_rejected() -> None:
    with pytest.raises(InvalidImageError, match="800 px"):
        process_image(make_image(640, 480))


def test_unsupported_formats_are_rejected() -> None:
    with pytest.raises(InvalidImageError, match="Format non accepté"):
        process_image(make_image(1200, 800, fmt="GIF"))


def test_non_image_content_is_rejected() -> None:
    with pytest.raises(InvalidImageError, match="pas une image valide"):
        process_image(b"<?php system($_GET['cmd']); ?>")
