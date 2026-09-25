"""Validation et conversion des images uploadées, sans accès disque ni base."""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

# Refuse les « bombes de décompression » : images minuscules qui explosent en mémoire.
Image.MAX_IMAGE_PIXELS = 40_000_000

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
MIN_WIDTH = 800
VARIANT_WIDTHS = {"sm": 400, "md": 1200, "lg": 2000}
WEBP_QUALITY = 82


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class ImageVariant:
    name: str
    width: int
    height: int
    content: bytes


@dataclass(frozen=True)
class ProcessedImage:
    width: int
    height: int
    variants: list[ImageVariant]


def process_image(data: bytes) -> ProcessedImage:
    image = _open_verified(data)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGBA" if image.has_transparency_data else "RGB")

    if image.width < MIN_WIDTH:
        raise InvalidImageError(f"L'image doit faire au moins {MIN_WIDTH} px de large.")

    variants: list[ImageVariant] = []
    for name, target_width in VARIANT_WIDTHS.items():
        resized = image.copy()
        resized.thumbnail((target_width, target_width * 10), Image.Resampling.LANCZOS)
        if variants and resized.width == variants[-1].width:
            continue
        buffer = BytesIO()
        resized.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
        variants.append(ImageVariant(name, resized.width, resized.height, buffer.getvalue()))

    return ProcessedImage(width=image.width, height=image.height, variants=variants)


def _open_verified(data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise InvalidImageError("Format non accepté : JPEG, PNG ou WebP uniquement.")
            probe.verify()
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise InvalidImageError("Le fichier n'est pas une image valide.") from exc
    return image
