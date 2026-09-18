"""File storage.

Files are written outside the web root under a generated name and served
back through an authorised endpoint, never by static path. Guessing a URL
must not be a way to read someone else's evidence.
"""

import hashlib
import os
import secrets
from pathlib import Path

from flask import current_app

from app.models.attachment import ALLOWED_MIME_TYPES, MAX_FILE_BYTES

# Signatures checked against the declared content type. A client can claim
# any MIME type, so the bytes are inspected rather than trusted.
MAGIC_NUMBERS = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\xd0\xcf\x11\xe0": "application/msword",
}


class StorageError(Exception):
    """Raised when a file is rejected."""


def upload_root() -> Path:
    root = Path(current_app.config["UPLOAD_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sniff(head: bytes) -> str | None:
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1"):
        return "image/heic"
    for signature, mime in MAGIC_NUMBERS.items():
        if head.startswith(signature):
            return mime
    return None


def validate(file_storage) -> tuple[str, int]:
    """Check declared type, real content and size.

    Returns the verified MIME type and the size in bytes.
    """
    declared = (file_storage.mimetype or "").lower()
    if declared not in ALLOWED_MIME_TYPES:
        raise StorageError(
            "That file type is not accepted. Attach an image, a PDF or a Word document."
        )

    head = file_storage.stream.read(32)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    if size == 0:
        raise StorageError("That file is empty.")
    if size > MAX_FILE_BYTES:
        raise StorageError(
            f"That file is too large. The limit is {MAX_FILE_BYTES // (1024 * 1024)} MB."
        )

    actual = _sniff(head)
    if actual is None:
        raise StorageError("We could not read that file. Try saving it again.")

    # A .docx and a .zip share a signature, so the family is compared
    # rather than the exact string.
    family = declared.split("/")[0]
    if actual != declared and actual.split("/")[0] != family:
        raise StorageError("That file does not match its type. Try saving it again.")

    return declared, size


def save(file_storage, institution_id: str) -> tuple[str, int]:
    """Persist a validated file and return its stored name and size."""
    mime, size = validate(file_storage)

    extension = ALLOWED_MIME_TYPES[mime]
    stored_name = f"{institution_id[:8]}_{secrets.token_urlsafe(24)}{extension}"

    destination = upload_root() / stored_name
    file_storage.save(destination)

    # Defend against a file that grows between validation and write.
    if destination.stat().st_size > MAX_FILE_BYTES:
        destination.unlink(missing_ok=True)
        raise StorageError("That file is too large.")

    return stored_name, size


def path_for(stored_name: str) -> Path:
    """Resolve a stored name to a path inside the upload directory.

    The resolved path is confirmed to sit under the root so a crafted name
    cannot escape it.
    """
    root = upload_root().resolve()
    candidate = (root / stored_name).resolve()
    if not str(candidate).startswith(str(root) + os.sep):
        raise StorageError("Invalid file reference.")
    return candidate


def delete(stored_name: str) -> None:
    try:
        path_for(stored_name).unlink(missing_ok=True)
    except StorageError:
        pass


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()
