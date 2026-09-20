"""Cloudinary backend.

The signature algorithm and the delivery type are the two things that
silently go wrong: a bad signature fails loudly in staging, but a public
delivery type works perfectly and quietly publishes complaint evidence to
the internet.
"""

import hashlib

from app.services import cloudinary_storage as cloudinary


def configure(app, folder="resolve/attachments"):
    app.config["CLOUDINARY_CLOUD_NAME"] = "demo-cloud"
    app.config["CLOUDINARY_API_KEY"] = "123456789"
    app.config["CLOUDINARY_API_SECRET"] = "secret-value"
    app.config["CLOUDINARY_FOLDER"] = folder


# -- configuration ----------------------------------------------------


def test_backend_is_off_until_configured(app):
    app.config["CLOUDINARY_CLOUD_NAME"] = None
    assert cloudinary.is_enabled() is False


def test_backend_needs_every_credential(app):
    """A half-configured provider must not silently swallow uploads."""
    configure(app)
    app.config["CLOUDINARY_API_SECRET"] = None

    assert cloudinary.is_enabled() is False


def test_backend_turns_on_when_fully_configured(app):
    configure(app)
    assert cloudinary.is_enabled() is True


def test_cloudinary_takes_precedence_over_supabase(app):
    """Both configured should not be ambiguous."""
    from app.services import storage

    configure(app)
    app.config["SUPABASE_URL"] = "https://ref.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = "key"
    app.config["SUPABASE_BUCKET"] = "attachments"

    assert storage.backend_name() == "cloudinary"


def test_local_disk_is_the_default(app):
    from app.services import storage

    app.config["CLOUDINARY_CLOUD_NAME"] = None
    app.config["SUPABASE_URL"] = None

    assert storage.backend_name() == "local"


# -- signing ----------------------------------------------------------


def test_signature_matches_the_documented_algorithm():
    """Sorted key=value pairs, secret appended, SHA-1."""
    params = {"timestamp": 1700000000, "public_id": "sample"}

    expected = hashlib.sha1(
        b"public_id=sample&timestamp=1700000000secret-value"
    ).hexdigest()

    assert cloudinary.sign(params, "secret-value") == expected


def test_signature_excludes_empty_values():
    """The API rejects a signature computed over blank parameters."""
    with_blank = cloudinary.sign({"a": "1", "b": ""}, "secret")
    without = cloudinary.sign({"a": "1"}, "secret")

    assert with_blank == without


def test_signature_is_order_independent():
    first = cloudinary.sign({"b": "2", "a": "1"}, "secret")
    second = cloudinary.sign({"a": "1", "b": "2"}, "secret")

    assert first == second


def test_signature_changes_with_the_secret():
    params = {"public_id": "sample", "timestamp": 1700000000}

    assert cloudinary.sign(params, "one") != cloudinary.sign(params, "two")


# -- resource typing --------------------------------------------------


def test_images_are_typed_as_image_with_a_separate_format(app):
    """Cloudinary keeps the format apart from the public id for images."""
    configure(app)

    resource_type, public_id, file_format = cloudinary.describe("abc123_photo.png")

    assert resource_type == "image"
    assert file_format == "png"
    assert public_id.endswith("abc123_photo")
    assert not public_id.endswith(".png")


def test_documents_are_typed_as_raw_keeping_the_extension(app):
    """For raw assets the extension is part of the public id."""
    configure(app)

    resource_type, public_id, file_format = cloudinary.describe("abc123_receipt.pdf")

    assert resource_type == "raw"
    assert file_format == ""
    assert public_id.endswith("abc123_receipt.pdf")


def test_the_folder_prefixes_the_public_id(app):
    configure(app, folder="resolve/attachments")

    _, public_id, _ = cloudinary.describe("abc123_photo.jpg")

    assert public_id.startswith("resolve/attachments/")


def test_an_empty_folder_is_handled(app):
    """A leading slash would create an unnamed folder."""
    configure(app, folder="")

    _, public_id, _ = cloudinary.describe("abc123_photo.jpg")

    assert not public_id.startswith("/")
    assert public_id == "abc123_photo"


def test_every_extension_round_trips(app):
    """Upload, download and delete must agree on the resource type."""
    configure(app)

    for name, expected in [
        ("a_x.jpg", "image"),
        ("a_x.jpeg", "image"),
        ("a_x.png", "image"),
        ("a_x.webp", "image"),
        ("a_x.heic", "image"),
        ("a_x.pdf", "raw"),
        ("a_x.docx", "raw"),
        ("a_x.doc", "raw"),
    ]:
        resource_type, _, _ = cloudinary.describe(name)
        assert resource_type == expected, name


# -- delivery type ----------------------------------------------------


def test_uploads_are_never_public(app, monkeypatch):
    """Cloudinary defaults to a public CDN asset.

    These are complaint attachments. A public delivery type would publish
    evidence about harassment or health to anyone with the URL.
    """
    configure(app)
    captured = {}

    def fake_post(url, fields, file_payload=None):
        captured["url"] = url
        captured["fields"] = fields
        return {}

    monkeypatch.setattr(cloudinary, "_post", fake_post)
    cloudinary.upload("abc123_photo.png", b"bytes", "image/png")

    assert captured["fields"]["type"] == "authenticated"
    assert "/image/upload" in captured["url"]


def test_downloads_request_the_authenticated_asset(app, monkeypatch):
    configure(app)
    captured = {}

    class FakeResponse:
        def read(self):
            return b"file-bytes"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(url, timeout=None):
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(cloudinary.urllib.request, "urlopen", fake_urlopen)
    payload = cloudinary.download("abc123_photo.png")

    assert payload == b"file-bytes"
    assert "type=authenticated" in captured["url"]
    assert "signature=" in captured["url"]


def test_download_urls_expire(app, monkeypatch):
    """A signed URL that never expires is a permanent public link."""
    configure(app)
    captured = {}

    class FakeResponse:
        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(
        cloudinary.urllib.request,
        "urlopen",
        lambda url, timeout=None: (captured.update(url=url), FakeResponse())[1],
    )
    cloudinary.download("abc123_receipt.pdf")

    assert "expires_at=" in captured["url"]


def test_a_missing_asset_does_not_block_erasure(app, monkeypatch):
    """Deleting something already gone is the desired end state."""
    configure(app)

    def fail(*_args, **_kwargs):
        raise cloudinary.CloudinaryError("404 not found")

    monkeypatch.setattr(cloudinary, "_post", fail)

    # Must not raise: an erasure request cannot be held up by a file that
    # has already disappeared.
    cloudinary.delete("abc123_photo.png")


# -- integration with the storage layer -------------------------------


def test_storage_routes_uploads_to_cloudinary(app, monkeypatch):
    from app.services import storage

    configure(app)
    captured = {}

    monkeypatch.setattr(
        cloudinary,
        "upload",
        lambda name, payload, content_type: captured.update(
            name=name, size=len(payload), content_type=content_type
        ),
    )

    storage.write_bytes("abc123_photo.webp", b"preview-bytes", "image/webp")

    assert captured["name"] == "abc123_photo.webp"
    assert captured["content_type"] == "image/webp"


def test_a_storage_failure_becomes_a_readable_message(app, monkeypatch):
    """A provider outage should not surface a stack trace to a student."""
    import pytest

    from app.services import storage

    configure(app)

    def fail(*_args, **_kwargs):
        raise cloudinary.CloudinaryError("upstream exploded")

    monkeypatch.setattr(cloudinary, "upload", fail)

    with pytest.raises(storage.StorageError, match="could not store"):
        storage.write_bytes("abc123_photo.webp", b"bytes", "image/webp")
