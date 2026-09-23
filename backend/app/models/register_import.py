"""Archive of student register imports.

A register import is not a one-off. It is the source of truth for who
is a student, and an institution may need to prove what was imported,
when and by whom. The file itself is kept – in Cloudinary when
available (free tier: 25GB storage, authenticated raw, never public),
otherwise on local disk via the existing storage backend – and a row
here records its location.

This also answers the question \"can student register import be stored
in Cloudinary storage?\" – yes, and it should be, because Render's
filesystem is ephemeral. A register uploaded today would otherwise
disappear on the next deploy.
"""

from app.extensions import db
from app.models.base import TimestampMixin, fk, new_uuid


class RegisterImport(TimestampMixin, db.Model):
    __tablename__ = "register_imports"
    __table_args__ = (
        db.Index("ix_register_import_institution_created", "institution_id", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )
    session_id = db.Column(
        db.String(36), db.ForeignKey(fk("academic_sessions.id"), ondelete="SET NULL"), index=True
    )

    # Who uploaded
    uploaded_by_user_id = db.Column(db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"))

    # Original file name as supplied by the browser
    original_filename = db.Column(db.String(255), nullable=False)

    # Where the bytes live: stored_name understood by storage backend
    stored_name = db.Column(db.String(500), nullable=False)
    storage_backend = db.Column(db.String(20), default="local", nullable=False)  # local | cloudinary | supabase

    content_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer, nullable=False)

    # Stats from the import
    rows_read = db.Column(db.Integer, default=0)
    created_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)
    problems_json = db.Column(db.JSON)

    dry_run = db.Column(db.Boolean, default=False, nullable=False)

    institution = db.relationship("Institution", backref=db.backref("register_imports", lazy="dynamic"))
    session = db.relationship("AcademicSession")
    uploaded_by = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "institution_id": self.institution_id,
            "session_id": self.session_id,
            "session_name": self.session.name if self.session else None,
            "uploaded_by": self.uploaded_by.full_name if self.uploaded_by else None,
            "original_filename": self.original_filename,
            "storage_backend": self.storage_backend,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "rows_read": self.rows_read,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<RegisterImport {self.original_filename} {self.size_bytes}B>"
