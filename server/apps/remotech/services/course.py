import io
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_WIDTH = 1600
WEBP_QUALITY = 80


def convert_to_webp(uploaded_file):
    """Validate an uploaded image and convert it to WebP.

    Returns an InMemoryUploadedFile named `<original>.webp` so that the
    conversion applies transparently on create, update and partial update.
    """
    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise ValidationError("Thumbnail must be 10 MB or smaller.")

    try:
        image = Image.open(uploaded_file)
        image.load()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Thumbnail must be a valid image file.")

    image = ImageOps.exif_transpose(image)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    if image.width > MAX_WIDTH:
        height = round(image.height * MAX_WIDTH / image.width)
        image = image.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
    size = buffer.tell()
    buffer.seek(0)

    name = f"{Path(uploaded_file.name).stem}.webp"
    return InMemoryUploadedFile(
        buffer,
        "ImageField",
        name,
        "image/webp",
        size,
        None,
    )
