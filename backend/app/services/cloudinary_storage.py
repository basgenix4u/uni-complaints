"""Cloudinary backend for attachments.

Cloudinary uploads default to the `upload` delivery type, which is public
on the CDN. For a complaints system that would publish evidence about
harassment, health and misconduct to anyone who guessed or was sent a URL.

Everything here is uploaded as `authenticated`, where the original and any
derived version require a signed request. Files are then fetched by the API
using a short-lived signed download URL and streamed to the caller only
after the usual permission checks, exactly as with the other backends. No
Cloudinary URL is ever handed to a browser.
"""

import hashlib
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from flask import current_app

API_BASE = "https://api.cloudinary.com/v1_1"

# Cloudinary splits assets by resource type, and the same value must be
# used to upload, download and delete. It is derived from the extension so
# both ends agree without storing an extra column.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"}

# How long a generated download URL stays valid. The API fetches the bytes
# immediately, so this only needs to cover one request.
DOWNLOAD_TTL_SECONDS = 120


class CloudinaryError(Exception):
    """Raised when Cloudinary rejects an operation."""


def is_enabled() -> bool:
    return bool(
        current_app.config.get("CLOUDINARY_CLOUD_NAME")
        and current_app.config.get("CLOUDINARY_API_KEY")
        and current_app.config.get("CLOUDINARY_API_SECRET")
    )


def _credentials() -> tuple[str, str, str]:
    return (
        current_app.config["CLOUDINARY_CLOUD_NAME"],
        current_app.config["CLOUDINARY_API_KEY"],
        current_app.config["CLOUDINARY_API_SECRET"],
    )


def describe(stored_name: str) -> tuple[str, str, str]:
    """Split a stored name into resource type, public id and format.

    For a raw asset Cloudinary treats the extension as part of the public
    id; for an image the format is separate. Getting this wrong produces a
    404 on download, so it is derived in one place.
    """
    suffix = Path(stored_name).suffix.lower()
    folder = current_app.config.get("CLOUDINARY_FOLDER", "").strip("/")

    if suffix in IMAGE_EXTENSIONS:
        stem = Path(stored_name).stem
        public_id = f"{folder}/{stem}" if folder else stem
        return "image", public_id, suffix.lstrip(".")

    public_id = f"{folder}/{stored_name}" if folder else stored_name
    return "raw", public_id, ""


def sign(params: dict, api_secret: str) -> str:
    """Cloudinary request signature.

    Parameters are sorted by name, joined as key=value pairs, the secret is
    appended, and the result is hashed with SHA-1. Empty values are
    excluded, which the API requires.
    """
    payload = "&".join(
        f"{key}={params[key]}"
        for key in sorted(params)
        if params[key] not in (None, "")
    )
    return hashlib.sha1(f"{payload}{api_secret}".encode()).hexdigest()


def _post(url: str, fields: dict, file_payload: tuple[str, bytes, str] | None = None) -> dict:
    """Send a multipart or form encoded request."""
    if file_payload is None:
        body = urllib.parse.urlencode(
            {k: v for k, v in fields.items() if v not in (None, "")}
        ).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
    else:
        boundary = uuid.uuid4().hex
        filename, content, content_type = file_payload
        parts = []

        for key, value in fields.items():
            if value in (None, ""):
                continue
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            )

        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n".encode()
        )
        parts.append(content)
        parts.append(f"\r\n--{boundary}--\r\n".encode())

        body = b"".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        raise CloudinaryError(
            f"Cloudinary returned {error.code}: {error.read().decode()[:300]}"
        ) from error
    except urllib.error.URLError as error:
        raise CloudinaryError(f"Could not reach Cloudinary: {error.reason}") from error


def upload(stored_name: str, payload: bytes, content_type: str) -> None:
    cloud, api_key, api_secret = _credentials()
    resource_type, public_id, _ = describe(stored_name)

    params = {
        "public_id": public_id,
        "timestamp": int(time.time()),
        # Without this the asset is public on the CDN. Everything stored
        # here is evidence attached to a complaint, so the original and
        # every derived version must require a signed request.
        "type": "authenticated",
        # A complaint attachment should never surface in a search engine.
        "invalidate": "true",
    }
    params["signature"] = sign(params, api_secret)
    params["api_key"] = api_key

    _post(
        f"{API_BASE}/{cloud}/{resource_type}/upload",
        params,
        file_payload=(Path(stored_name).name, payload, content_type),
    )


def download(stored_name: str) -> bytes:
    """Fetch an asset through a short-lived signed request."""
    cloud, api_key, api_secret = _credentials()
    resource_type, public_id, file_format = describe(stored_name)

    params = {
        "public_id": public_id,
        "resource_type": resource_type,
        "type": "authenticated",
        "timestamp": int(time.time()),
        "expires_at": int(time.time()) + DOWNLOAD_TTL_SECONDS,
        "attachment": "true",
    }
    if file_format:
        params["format"] = file_format

    params["signature"] = sign(params, api_secret)
    params["api_key"] = api_key

    url = f"{API_BASE}/{cloud}/{resource_type}/download?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise CloudinaryError(
            f"Cloudinary returned {error.code}: {error.read().decode()[:200]}"
        ) from error
    except urllib.error.URLError as error:
        raise CloudinaryError(f"Could not reach Cloudinary: {error.reason}") from error


def delete(stored_name: str) -> None:
    cloud, api_key, api_secret = _credentials()
    resource_type, public_id, _ = describe(stored_name)

    params = {
        "public_id": public_id,
        "type": "authenticated",
        "timestamp": int(time.time()),
        "invalidate": "true",
    }
    params["signature"] = sign(params, api_secret)
    params["api_key"] = api_key

    try:
        _post(f"{API_BASE}/{cloud}/{resource_type}/destroy", params)
    except CloudinaryError:
        # An asset that is already gone is the desired end state. Raising
        # would block an erasure request over a missing file.
        current_app.logger.warning("Could not delete %s from Cloudinary", stored_name)


def guess_content_type(stored_name: str) -> str:
    return mimetypes.guess_type(stored_name)[0] or "application/octet-stream"
