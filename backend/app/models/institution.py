"""Institution (tenant) and its departments."""

from app.extensions import db
from app.models.base import TimestampMixin, new_uuid


class Institution(TimestampMixin, db.Model):
    """A tenant: one university, polytechnic, college or agency."""

    __tablename__ = "institutions"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)

    name = db.Column(db.String(200), nullable=False)
    # Appears in ticket IDs, e.g. "NGX" in NGX-7K2M-4318.
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)

    type = db.Column(db.String(40), default="university", nullable=False)
    state = db.Column(db.String(60))

    logo_url = db.Column(db.String(500))
    # Brand hue in degrees; the palette is generated from this while
    # preserving the contrast ratios defined in the design system.
    brand_hue = db.Column(db.Integer, default=162, nullable=False)

    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(30))

    default_sla_hours = db.Column(db.Integer, default=72, nullable=False)
    acknowledge_sla_hours = db.Column(db.Integer, default=24, nullable=False)
    # SLA clocks pause outside these hours so a Friday evening complaint is
    # not already breached by Monday morning.
    working_hours_start = db.Column(db.Integer, default=8, nullable=False)
    working_hours_end = db.Column(db.Integer, default=17, nullable=False)

    allow_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    ticket_sequence = db.Column(db.Integer, default=0, nullable=False)

    departments = db.relationship(
        "Department", back_populates="institution", cascade="all, delete-orphan", lazy="dynamic"
    )
    users = db.relationship(
        "User", back_populates="institution", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_settings: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "slug": self.slug,
            "type": self.type,
            "state": self.state,
            "logo_url": self.logo_url,
            "brand_hue": self.brand_hue,
            "is_active": self.is_active,
        }
        if include_settings:
            data.update(
                {
                    "contact_email": self.contact_email,
                    "contact_phone": self.contact_phone,
                    "default_sla_hours": self.default_sla_hours,
                    "acknowledge_sla_hours": self.acknowledge_sla_hours,
                    "working_hours_start": self.working_hours_start,
                    "working_hours_end": self.working_hours_end,
                    "allow_anonymous": self.allow_anonymous,
                }
            )
        return data

    def __repr__(self) -> str:
        return f"<Institution {self.code}>"


class Department(TimestampMixin, db.Model):
    """A routing target within an institution."""

    __tablename__ = "departments"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "slug", name="uq_department_slug_per_institution"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(400))

    # Overrides the institution default when set.
    sla_hours = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    institution = db.relationship("Institution", back_populates="departments")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "sla_hours": self.sla_hours,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<Department {self.slug}>"
