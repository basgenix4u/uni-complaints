"""File attachments on complaints and replies."""

from app.extensions import db
from app.models.base import TimestampMixin, new_uuid

# Evidence for a complaint is realistically a photo, a scan or a document.
# Archives and executables are excluded: they cannot be previewed, and
# accepting them turns the upload endpoint into a malware channel.
ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES_PER_COMPLAINT = 5


class Attachment(TimestampMixin, db.Model):
    __tablename__ = "attachments"
    __table_args__ = (db.Index("ix_attachment_complaint", "complaint_id", "created_at"),)

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id = db.Column(
        db.String(36), db.ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_id = db.Column(db.String(36), db.ForeignKey("responses.id", ondelete="CASCADE"))
    uploaded_by_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"))

    # The name the user recognises, kept only for display.
    original_name = db.Column(db.String(255), nullable=False)
    # Generated name on disk. User input never reaches the filesystem.
    stored_name = db.Column(db.String(120), nullable=False, unique=True)
    mime_type = db.Column(db.String(120), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)

    # Attached to an internal note, so students must not see it.
    is_internal = db.Column(db.Boolean, default=False, nullable=False)

    # Downscaled preview, written beside the original where the format
    # allows it. Absent for documents and where Pillow is not installed.
    thumbnail_name = db.Column(db.String(120))

    uploader = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "is_image": self.mime_type.startswith("image/"),
            "has_preview": bool(self.thumbnail_name),
            "is_internal": self.is_internal,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "uploaded_by": self.uploader.full_name if self.uploader else None,
        }

    def __repr__(self) -> str:
        return f"<Attachment {self.original_name}>"
