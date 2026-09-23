"""Institution (tenant) and its departments."""

from app.extensions import db
from app.models.base import fk, TimestampMixin, new_uuid

# The vocabulary for `type`, in one place because two of them had already
# drifted apart: the imported register wrote "college_of_education" while
# the manual form wrote "college", so a filter for one silently excluded
# the other and neither the caller nor the log said anything.
INSTITUTION_TYPES = (
    "university",
    "polytechnic",
    "college_of_education",
    "teaching_hospital",
    "agency",
)

# Older and shorter spellings that reached the database or a query string
# before the vocabulary was settled. Accepting them costs nothing and
# means a bookmarked filter keeps working.
TYPE_ALIASES = {
    "college": "college_of_education",
    "colleges_of_education": "college_of_education",
    "coe": "college_of_education",
    "hospital": "teaching_hospital",
    "poly": "polytechnic",
    "uni": "university",
}


def canonical_type(value: str | None) -> str | None:
    """Map a supplied type onto the vocabulary, or None if unrecognised."""
    key = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        return None
    key = TYPE_ALIASES.get(key, key)
    return key if key in INSTITUTION_TYPES else None


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

    # What people actually call the place. Distinct from `code`, which
    # prefixes every ticket number and so has to stay unique: acronyms do
    # not. Several institutions answer to ACE, and a student searching
    # "UNILAG" should find Lagos whatever its ticket prefix happens to be.
    short_name = db.Column(db.String(20), index=True)

    # How the institution is funded. Two institutions in different states
    # often share a name, and this is what tells them apart in a list.
    ownership = db.Column(db.String(20))

    logo_url = db.Column(db.String(500))
    # Brand hue in degrees; the palette is generated from this while
    # preserving the contrast ratios defined in the design system.
    brand_hue = db.Column(db.Integer, default=162, nullable=False)

    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(30))

    default_sla_hours = db.Column(db.Integer, default=72, nullable=False)
    acknowledge_sla_hours = db.Column(db.Integer, default=24, nullable=False)

    # Optional per-priority policy. Null preserves the institution's old
    # behaviour: one acknowledgement target, the existing resolution
    # factors, and a 24-hour escalation rung. A populated policy can
    # tighten urgent cases without silently changing every existing
    # institution during migration.
    priority_sla_policy = db.Column(db.JSON)

    # SLA clocks pause outside these hours so a Friday evening complaint is
    # not already breached by Monday morning.
    working_hours_start = db.Column(db.Integer, default=8, nullable=False)
    working_hours_end = db.Column(db.Integer, default=17, nullable=False)

    allow_anonymous = db.Column(db.Boolean, default=False, nullable=False)

    # Months a closed complaint is kept before the purge removes it.
    # Zero disables the purge, which is a deliberate choice an institution
    # has to make rather than a default that quietly keeps data forever.
    retention_months = db.Column(db.Integer, default=0, nullable=False)

    # How a person proves they are a student here.
    #
    #   register  matched against the uploaded student register. The
    #             strongest option, and the default, because it also
    #             fills in faculty, department and level.
    #   open      any email, confirmed by a link. For institutions
    #             without a usable register.
    #   manual    an administrator approves each registration.
    #
    # Requiring a university email is deliberately not an option on its
    # own: many students never receive one.
    verification_mode = db.Column(db.String(20), default="register", nullable=False)

    # Matriculation formats differ between institutions, so the pattern
    # is data rather than a single regex in code.
    matric_pattern = db.Column(db.String(200))
    matric_example = db.Column(db.String(60))

    # Last time the head was sent the list of complaints the institution
    # has ignored. Recorded so a scheduler running every quarter of an
    # hour sends a weekly report rather than a weekly report every
    # quarter of an hour.
    ignored_report_sent_at = db.Column(db.DateTime(timezone=True))

    # Shown to a student whose institution is not yet using the service,
    # and counted as demand.
    is_onboarded = db.Column(db.Boolean, default=False, nullable=False)
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
            # Carried here as well as in the directory payload: the
            # platform admin picks an institution out of several hundred
            # and needs the same acronym and ownership to tell near
            # identical names apart.
            "short_name": self.short_name,
            "type": self.type,
            "state": self.state,
            "ownership": self.ownership,
            "logo_url": self.logo_url,
            "brand_hue": self.brand_hue,
            "is_active": self.is_active,
            "is_onboarded": self.is_onboarded,
            # Not a setting: a student has to know before writing whether
            # this can be sent without their name on it, and the answer
            # changes what they are willing to report.
            "allow_anonymous": self.allow_anonymous,
        }
        if include_settings:
            data.update(
                {
                    "contact_email": self.contact_email,
                    "contact_phone": self.contact_phone,
                    "default_sla_hours": self.default_sla_hours,
                    "acknowledge_sla_hours": self.acknowledge_sla_hours,
                    "priority_sla_policy": self.priority_sla_policy,
                    "working_hours_start": self.working_hours_start,
                    "working_hours_end": self.working_hours_end,
                    "retention_months": self.retention_months,
                    "verification_mode": self.verification_mode,
                    "matric_pattern": self.matric_pattern,
                    "matric_example": self.matric_example,
                }
            )
        return data

    def to_directory_dict(self) -> dict:
        """The public listing, for someone choosing where they study.

        Deliberately thin. This is served without authentication, so it
        carries only what a person needs to recognise their own
        institution and see whether it is using the service.
        """
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "short_name": self.short_name,
            "type": self.type,
            "state": self.state,
            "ownership": self.ownership,
            "logo_url": self.logo_url,
            "is_onboarded": self.is_onboarded and self.is_active,
            # Tells the sign-up form what to ask for, so a student is not
            # made to type a matriculation number that will not be checked.
            "verification_mode": self.verification_mode if self.is_onboarded else None,
            "matric_example": self.matric_example,
        }

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
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
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
