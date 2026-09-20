"""Object storage backend for attachments.

Render, Railway, Fly and most container hosts give a container an ephemeral
filesystem. Anything written to disk disappears on the next deploy, restart
or scale event, so uploaded evidence would silently vanish.

Supabase Storage is used when configured, falling back to local disk for
development. The bucket must be private: files are fetched by the API using
the service key and streamed to the caller only after the same
authorisation checks as before, so a leaked URL reveals nothing.
"""

import json
import urllib.error
import urllib.request

from flask import current_app


class ObjectStorageError(Exception):
    """Raised when the storage backend rejects an operation."""


def is_enabled() -> bool:
    return bool(
        current_app.config.get("SUPABASE_URL")
        and current_app.config.get("SUPABASE_SERVICE_KEY")
        and current_app.config.get("SUPABASE_BUCKET")
    )


def _endpoint(stored_name: str) -> str:
    base = current_app.config["SUPABASE_URL"].rstrip("/")
    bucket = current_app.config["SUPABASE_BUCKET"]
    return f"{base}/storage/v1/object/{bucket}/{stored_name}"


def _headers(extra: dict | None = None) -> dict:
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    headers.update(extra or {})
    return headers


def _request(url: str, method: str, data: bytes | None = None, headers: dict | None = None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode()[:300]
        raise ObjectStorageError(f"Storage returned {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise ObjectStorageError(f"Could not reach storage: {error.reason}") from error


def upload(stored_name: str, payload: bytes, content_type: str) -> None:
    _request(
        _endpoint(stored_name),
        "POST",
        data=payload,
        headers=_headers(
            {
                "Content-Type": content_type,
                # Names are generated, so a collision means a bug rather
                # than a legitimate overwrite.
                "x-upsert": "false",
            }
        ),
    )


def download(stored_name: str) -> bytes:
    return _request(_endpoint(stored_name), "GET", headers=_headers())


def delete(stored_name: str) -> None:
    try:
        _request(
            f"{current_app.config['SUPABASE_URL'].rstrip('/')}/storage/v1/object/"
            f"{current_app.config['SUPABASE_BUCKET']}",
            "DELETE",
            data=json.dumps({"prefixes": [stored_name]}).encode(),
            headers=_headers({"Content-Type": "application/json"}),
        )
    except ObjectStorageError:
        # A file that is already gone is the desired end state. Failing
        # here would block an erasure request over a missing object.
        current_app.logger.warning("Could not delete %s from storage", stored_name)
