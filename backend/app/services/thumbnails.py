"""Image previews.

A queue of attachments is far quicker to work through when staff can see
what a photograph shows without downloading it. Pillow is optional, so a
deployment without it keeps working and simply serves no previews.
"""

import io
from pathlib import Path

from flask import current_app

try:  # pragma: no cover - exercised by whether the package is installed
    from PIL import Image, UnidentifiedImageError

    PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    PILLOW_AVAILABLE = False

THUMBNAIL_MAX = (480, 480)
THUMBNAIL_SUFFIX = "_thumb.webp"

# Formats Pillow can open safely for preview purposes. HEIC needs a plugin
# that is often absent, so it is not assumed.
PREVIEWABLE = {"image/jpeg", "image/png", "image/webp"}


def can_preview(mime_type: str) -> bool:
    return PILLOW_AVAILABLE and mime_type in PREVIEWABLE


def thumbnail_name(stored_name: str) -> str:
    return Path(stored_name).stem + THUMBNAIL_SUFFIX


def generate_from_bytes(payload: bytes, stored_name: str) -> str | None:
    """Build a downscaled preview and hand it back to storage.

    Returns the preview name, or None when one could not be produced. A
    failure here must never fail the upload: the original is already
    stored and is what matters.
    """
    if not PILLOW_AVAILABLE:
        return None

    from app.services import storage

    target_name = thumbnail_name(stored_name)
    buffer = io.BytesIO()

    try:
        with Image.open(io.BytesIO(payload)) as image:
            # Copying pixel data drops EXIF. Photographs taken on a phone
            # carry GPS coordinates, and a complaint about a hostel should
            # not disclose where the student was standing.
            image = image.convert("RGB")
            image.thumbnail(THUMBNAIL_MAX)
            image.save(buffer, "WEBP", quality=78, method=4)
        storage.write_bytes(target_name, buffer.getvalue(), "image/webp")
    except (UnidentifiedImageError, OSError, ValueError, Exception):
        current_app.logger.warning("Could not create a preview for %s", stored_name)
        return None

    return target_name


def remove(stored_name: str, directory: Path) -> None:
    (directory / thumbnail_name(stored_name)).unlink(missing_ok=True)
