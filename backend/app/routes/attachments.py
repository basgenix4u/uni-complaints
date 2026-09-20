"""Attachment upload and download."""

import io

from flask import Blueprint, g, request, send_file

from app.extensions import db, limiter
from app.models.attachment import MAX_FILES_PER_COMPLAINT, Attachment
from app.models.complaint import Complaint
from app.routes.auth import fail, ok
from app.security import auth_required, can_view_complaint, tenant_query
from app.services import storage, thumbnails
from app.services.notifications import record_event

bp = Blueprint("attachments", __name__, url_prefix="/api/complaints")


@bp.post("/<complaint_id>/attachments")
@auth_required()
@limiter.limit("30 per hour")
def upload(complaint_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that complaint.", 404)

    if complaint.status in ("closed", "declined"):
        return fail("This complaint is closed, so files can no longer be added.", 409)

    file_storage = request.files.get("file")
    if not file_storage or not file_storage.filename:
        return fail("Choose a file to attach.", 422, {"file": "Choose a file to attach."})

    existing = Attachment.query.filter_by(complaint_id=complaint.id).count()
    if existing >= MAX_FILES_PER_COMPLAINT:
        return fail(
            f"You can attach up to {MAX_FILES_PER_COMPLAINT} files to one complaint.", 409
        )

    try:
        stored_name, size = storage.save(file_storage, complaint.institution_id)
    except storage.StorageError as error:
        return fail(str(error), 422, {"file": str(error)})

    # A preview is a convenience; failing to build one must not fail the
    # upload, since the original is already stored.
    preview = None
    if thumbnails.can_preview(file_storage.mimetype.lower()):
        try:
            preview = thumbnails.generate_from_bytes(storage.read(stored_name), stored_name)
        except storage.StorageError:
            preview = None

    # Only staff may mark an attachment private.
    is_internal = bool(request.form.get("is_internal")) and user.is_staff

    attachment = Attachment(
        institution_id=complaint.institution_id,
        complaint_id=complaint.id,
        uploaded_by_id=user.id,
        original_name=file_storage.filename[:255],
        stored_name=stored_name,
        mime_type=file_storage.mimetype.lower(),
        size_bytes=size,
        thumbnail_name=preview,
        is_internal=is_internal,
    )
    db.session.add(attachment)
    record_event(complaint, user.id, "attached", to_value=attachment.original_name)
    db.session.commit()

    return ok({"attachment": attachment.to_dict()}, "File attached.", 201)


@bp.get("/<complaint_id>/attachments/<attachment_id>")
@auth_required()
def download(complaint_id, attachment_id):
    """Serve a file only to someone entitled to the complaint.

    Files are stored outside the web root, so this endpoint is the only
    route to them and authorisation cannot be bypassed by guessing a path.
    """
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that file.", 404)

    attachment = Attachment.query.filter_by(
        id=attachment_id, complaint_id=complaint.id
    ).first()

    if not attachment:
        return fail("We could not find that file.", 404)

    # An attachment on an internal note is invisible to the student.
    if attachment.is_internal and not user.is_staff:
        return fail("We could not find that file.", 404)

    try:
        payload = storage.read(attachment.stored_name)
    except storage.StorageError:
        return fail("That file is no longer available.", 410)

    return send_file(
        io.BytesIO(payload),
        mimetype=attachment.mime_type,
        as_attachment=True,
        download_name=attachment.original_name,
        max_age=0,
    )


@bp.get("/<complaint_id>/attachments/<attachment_id>/preview")
@auth_required()
def preview(complaint_id, attachment_id):
    """Serve the downscaled preview.

    Carries the same checks as the original: a preview of a private
    attachment is still private.
    """
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that file.", 404)

    attachment = Attachment.query.filter_by(
        id=attachment_id, complaint_id=complaint.id
    ).first()

    if not attachment or not attachment.thumbnail_name:
        return fail("We could not find that file.", 404)
    if attachment.is_internal and not user.is_staff:
        return fail("We could not find that file.", 404)

    try:
        payload = storage.read(attachment.thumbnail_name)
    except storage.StorageError:
        return fail("That file is no longer available.", 410)

    return send_file(io.BytesIO(payload), mimetype="image/webp", max_age=0)


@bp.delete("/<complaint_id>/attachments/<attachment_id>")
@auth_required()
def remove(complaint_id, attachment_id):
    user = g.current_user
    complaint = tenant_query(Complaint).filter_by(id=complaint_id).first()

    if not complaint or not can_view_complaint(user, complaint):
        return fail("We could not find that file.", 404)

    attachment = Attachment.query.filter_by(
        id=attachment_id, complaint_id=complaint.id
    ).first()
    if not attachment:
        return fail("We could not find that file.", 404)

    # The uploader may withdraw their own file; staff may remove any.
    if attachment.uploaded_by_id != user.id and not user.is_staff:
        return fail("You can only remove files you attached.", 403)

    storage.delete(attachment.stored_name)
    if attachment.thumbnail_name:
        storage.delete(attachment.thumbnail_name)
    record_event(complaint, user.id, "attachment_removed", from_value=attachment.original_name)
    db.session.delete(attachment)
    db.session.commit()

    return ok(message="File removed.")
