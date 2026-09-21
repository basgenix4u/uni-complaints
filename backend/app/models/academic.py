"""Academic structure and the student register.

A university has two hierarchies. The administrative one already exists as
`Department`: Bursary, Registry, Student Affairs, the units that resolve
complaints. This module adds the academic one, which is where a student
actually sits:

    Faculty -> AcademicDepartment -> Programme

The two are separate because a complaint can belong to either. A fee
receipt goes to Bursary, an administrative unit. A disputed grade goes to
the student's own department, which is academic. Modelling both as one
flat list, as the demo did, cannot express that difference.

The register exists because verifying a student is otherwise impossible.
Requiring a university email excludes the many students who never receive
one; accepting any email lets anyone claim to be a student anywhere. Every
registry already holds a spreadsheet of matriculation numbers, so matching
against it is both stronger and less work for the student, whose faculty,
department and level are then filled in rather than typed.
"""

from app.extensions import db
from app.models.base import TimestampMixin, fk, new_uuid, utcnow

# Where a student stands with the institution. Only `active` may file a
# complaint; the rest are kept because a graduate may still be chasing a
# transcript, and the record explains why they can no longer sign in.
ENROLMENT_STATUSES = ("active", "graduated", "withdrawn", "suspended", "deferred")


class AcademicSession(TimestampMixin, db.Model):
    """One academic year, such as 2025/2026.

    Admissions happen every session, so the register is not loaded once
    and forgotten. Each import is tied to a session, which makes it
    possible to see which intake a student came from and to keep previous
    years rather than overwriting them.
    """

    __tablename__ = "academic_sessions"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "name", name="uq_session_name_per_institution"),
        db.Index("ix_session_institution_current", "institution_id", "is_current"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Written as the institution writes it, for example "2025/2026".
    name = db.Column(db.String(20), nullable=False)
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)

    # Exactly one session is current per institution; the service layer
    # enforces it when a new one is opened.
    is_current = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "starts_on": self.starts_on.isoformat() if self.starts_on else None,
            "ends_on": self.ends_on.isoformat() if self.ends_on else None,
            "is_current": self.is_current,
        }

    def __repr__(self) -> str:
        return f"<AcademicSession {self.name}>"


class Faculty(TimestampMixin, db.Model):
    """A faculty, college or school.

    Names differ between institutions, so this is data rather than a
    hardcoded list. The demo shipped ten faculties in the frontend and
    showed the same ten to every university, which is wrong for almost
    all of them.
    """

    __tablename__ = "faculties"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "slug", name="uq_faculty_slug_per_institution"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(20))

    # The Dean. Academic complaints escalate here from a department, which
    # the demo could not do because the role did not exist.
    # users.faculty_id points back here, so this pair is a cycle. Marked
    # as a known one, otherwise metadata cannot order create and drop.
    dean_user_id = db.Column(
        db.String(36),
        db.ForeignKey(fk("users.id"), ondelete="SET NULL", use_alter=True,
                      name="fk_faculties_dean_user_id_users"),
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    departments = db.relationship(
        "AcademicDepartment", back_populates="faculty",
        cascade="all, delete-orphan", lazy="selectin",
    )
    dean = db.relationship("User", foreign_keys=[dean_user_id])

    def to_dict(self, include_departments: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "code": self.code,
            "dean": self.dean.full_name if self.dean else None,
            "is_active": self.is_active,
        }
        if include_departments:
            data["departments"] = [d.to_dict() for d in self.departments if d.is_active]
        return data

    def __repr__(self) -> str:
        return f"<Faculty {self.slug}>"


class AcademicDepartment(TimestampMixin, db.Model):
    """A department within a faculty, such as Computer Engineering.

    Deliberately not the same table as the administrative `Department`.
    Sharing one table would mean a routing rule could send a fee complaint
    to Computer Engineering, which is meaningless.
    """

    __tablename__ = "academic_departments"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "slug", name="uq_acaddept_slug_per_institution"),
        db.Index("ix_acaddept_faculty", "faculty_id", "is_active"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )
    faculty_id = db.Column(
        db.String(36), db.ForeignKey(fk("faculties.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(20))

    # The Head of Department, who receives academic complaints from their
    # own students before they escalate to the Dean.
    head_user_id = db.Column(
        db.String(36),
        db.ForeignKey(fk("users.id"), ondelete="SET NULL", use_alter=True,
                      name="fk_academic_departments_head_user_id_users"),
    )

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    faculty = db.relationship("Faculty", back_populates="departments")
    head = db.relationship("User", foreign_keys=[head_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "code": self.code,
            "faculty_id": self.faculty_id,
            "faculty": self.faculty.name if self.faculty else None,
            "head": self.head.full_name if self.head else None,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<AcademicDepartment {self.slug}>"


class StudentRecord(TimestampMixin, db.Model):
    """One row of the institution's student register.

    Imported from the spreadsheet a registry already keeps. Registration
    is checked against this, so a person cannot claim to be a student who
    does not exist, and their faculty, department and level come from the
    institution's own data rather than a dropdown they guess at.

    The record is separate from `User` on purpose: it exists before the
    student signs up, and it survives if they never do.
    """

    __tablename__ = "student_records"
    __table_args__ = (
        db.UniqueConstraint(
            "institution_id", "matric_number", name="uq_student_matric_per_institution"
        ),
        db.Index("ix_student_record_status", "institution_id", "status"),
        db.Index("ix_student_record_claimed", "institution_id", "claimed_by_user_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Stored in the institution's own normalised form. Formats differ
    # widely, so the pattern is configured per institution rather than
    # fixed in code.
    matric_number = db.Column(db.String(40), nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)

    faculty_id = db.Column(db.String(36), db.ForeignKey(fk("faculties.id"), ondelete="SET NULL"))
    academic_department_id = db.Column(
        db.String(36), db.ForeignKey(fk("academic_departments.id"), ondelete="SET NULL")
    )
    programme = db.Column(db.String(150))
    level = db.Column(db.Integer)

    # Which intake this row came from, so a later import adds to the
    # register rather than replacing it.
    admitted_session_id = db.Column(
        db.String(36), db.ForeignKey(fk("academic_sessions.id"), ondelete="SET NULL")
    )

    status = db.Column(db.String(20), default="active", nullable=False)

    # Set when someone registers against this row. Prevents two people
    # claiming the same matriculation number.
    claimed_by_user_id = db.Column(
        db.String(36), db.ForeignKey(fk("users.id"), ondelete="SET NULL"), unique=True
    )
    claimed_at = db.Column(db.DateTime(timezone=True))

    faculty = db.relationship("Faculty")
    academic_department = db.relationship("AcademicDepartment")
    admitted_session = db.relationship("AcademicSession")
    claimed_by = db.relationship("User", foreign_keys=[claimed_by_user_id])

    @property
    def can_register(self) -> bool:
        """Only a current student may claim a record."""
        return self.status == "active" and self.claimed_by_user_id is None

    def claim(self, user) -> None:
        self.claimed_by_user_id = user.id
        self.claimed_at = utcnow()

    def to_dict(self, include_personal: bool = True) -> dict:
        data = {
            "id": self.id,
            "matric_number": self.matric_number,
            "programme": self.programme,
            "level": self.level,
            "status": self.status,
            "claimed": self.claimed_by_user_id is not None,
            "faculty": self.faculty.name if self.faculty else None,
            "department": self.academic_department.name if self.academic_department else None,
            "session": self.admitted_session.name if self.admitted_session else None,
        }
        if include_personal:
            data["full_name"] = self.full_name
        return data

    def __repr__(self) -> str:
        return f"<StudentRecord {self.matric_number}>"


class InstitutionInterest(TimestampMixin, db.Model):
    """A student asking for their institution to be added.

    Turning a dead end into a signal. A student whose school is not yet
    using the service currently sees only "we could not find that
    institution", which helps nobody. Recording the request means fifty
    students from one university becomes the argument for approaching
    that university.
    """

    __tablename__ = "institution_interest"
    __table_args__ = (
        db.UniqueConstraint("email", "institution_name", name="uq_interest_email_institution"),
        db.Index("ix_interest_name", "institution_name"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)

    # Free text: the institution may not exist in our directory at all.
    institution_name = db.Column(db.String(200), nullable=False)
    # Set where the student picked a known but not yet onboarded entry.
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="SET NULL")
    )

    email = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))
    notified_at = db.Column(db.DateTime(timezone=True))

    institution = db.relationship("Institution")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "institution_name": self.institution_name,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<InstitutionInterest {self.institution_name}>"
