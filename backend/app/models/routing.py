"""Routing rules.

The demo had no routing at all: a complaint carried a category and a
department, and nothing connected them, so everything landed in one
undifferentiated queue. This is the table that decides which unit answers
which kind of complaint.

Routing is data rather than code because it genuinely differs between
institutions. Scholarships sit with Bursary at one university and with
Student Affairs at another, and neither is wrong.
"""

from app.extensions import db
from app.models.base import TimestampMixin, fk, new_uuid

# Where a complaint is sent.
#
#   unit        a named administrative unit, such as Bursary
#   department  the complainant's own academic department, resolved at
#               the time of filing. Used for academic matters, where the
#               correct destination depends on who is complaining.
TARGET_TYPES = ("unit", "department")
SLA_PRIORITIES = ("low", "medium", "high", "urgent")


class PrioritySlaPolicy(TimestampMixin, db.Model):
    """Deadlines attached to urgency rather than a one-size institution default.

    A stolen bag after dark and a routine certificate enquiry should not
    receive the same acknowledgement window. The policy is data because
    the institution, not the software, owns those promises.
    """

    __tablename__ = "priority_sla_policies"
    __table_args__ = (
        db.UniqueConstraint(
            "institution_id", "priority", name="uq_sla_priority_per_institution"
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )
    priority = db.Column(db.String(20), nullable=False)
    acknowledge_hours = db.Column(db.Integer, nullable=False)
    resolve_hours = db.Column(db.Integer, nullable=False)
    escalation_step_hours = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "priority": self.priority,
            "acknowledge_hours": self.acknowledge_hours,
            "resolve_hours": self.resolve_hours,
            "escalation_step_hours": self.escalation_step_hours,
            "is_active": self.is_active,
        }


class RoutingRule(TimestampMixin, db.Model):
    __tablename__ = "routing_rules"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "category", name="uq_routing_category"),
        db.Index("ix_routing_institution", "institution_id", "is_active"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False, index=True,
    )

    category = db.Column(db.String(60), nullable=False)
    target_type = db.Column(db.String(20), default="unit", nullable=False)

    # Set when target_type is "unit". Null for "department", where the
    # destination is the complainant's own department.
    department_id = db.Column(
        db.String(36), db.ForeignKey(fk("departments.id"), ondelete="SET NULL")
    )

    # Where it goes if the first destination does not answer in time.
    escalates_to_department_id = db.Column(
        db.String(36), db.ForeignKey(fk("departments.id"), ondelete="SET NULL")
    )

    # Keeps a complaint out of the general queue. A harassment report
    # naming a lecturer must not be visible to that lecturer's own
    # colleagues, so it goes to a named group instead.
    is_confidential = db.Column(db.Boolean, default=False, nullable=False)

    # Overrides the institution default for this kind of complaint.
    sla_hours = db.Column(db.Integer)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    department = db.relationship("Department", foreign_keys=[department_id])
    escalates_to = db.relationship("Department", foreign_keys=[escalates_to_department_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "target_type": self.target_type,
            "department_id": self.department_id,
            "department": self.department.name if self.department else None,
            "escalates_to": self.escalates_to.name if self.escalates_to else None,
            "is_confidential": self.is_confidential,
            "sla_hours": self.sla_hours,
            "is_active": self.is_active,
        }

    def __repr__(self) -> str:
        return f"<RoutingRule {self.category} -> {self.target_type}>"


# A starting point offered during onboarding, based on how most Nigerian
# universities divide responsibility. Presented for review rather than
# applied silently: an institution will disagree with some of it, and
# correcting a draft is easier than building the table from nothing.
#
# (category, unit slug, target type, escalates to, confidential)
DEFAULT_ROUTING = (
    ("result_issues", "exams-records", "unit", "registry", False),
    ("examination", "exams-records", "unit", "registry", False),
    ("course_registration", None, "department", "registry", False),
    ("academic_advising", None, "department", None, False),
    ("department_issue", None, "department", "registry", False),
    ("faculty_issue", None, "department", "registry", False),
    ("transcript", "registry", "unit", None, False),
    ("certificate", "registry", "unit", None, False),
    ("id_card", "registry", "unit", None, False),
    ("clearance", "registry", "unit", None, False),
    ("admission", "admissions", "unit", "registry", False),
    ("registration", "registry", "unit", None, False),
    ("transfer", "registry", "unit", None, False),
    ("fees_payment", "bursary", "unit", None, False),
    ("scholarship", "bursary", "unit", "student-affairs", False),
    ("ict_portal", "ict", "unit", "registry", False),
    ("accommodation", "student-affairs", "unit", None, False),
    ("student_welfare", "student-affairs", "unit", None, False),
    ("sug_support", "sug", "unit", "student-affairs", False),
    ("facilities", "works", "unit", None, False),
    ("library", "library", "unit", None, False),
    ("medical", "health-services", "unit", None, False),
    # Safety matters are confidential by default. Getting this wrong is
    # not a routing error, it is a safeguarding failure.
    ("security", "security", "unit", "student-affairs", True),
    ("other", "student-affairs", "unit", None, False),
)

# The units almost every Nigerian university has. Created during
# onboarding so an administrator reviews a list rather than typing one.
DEFAULT_UNITS = (
    ("Registry", "registry", "Records, admissions, transcripts and certificates"),
    ("Exams and Records", "exams-records", "Results, examinations and transcripts"),
    ("Admissions", "admissions", "Admission and matriculation"),
    ("Bursary", "bursary", "Fees, receipts, refunds and scholarships"),
    ("Student Affairs", "student-affairs", "Hostel, welfare and discipline"),
    ("Students' Union Government", "sug", "Peer support and student representation"),
    ("ICT", "ict", "Portal, email and network faults"),
    ("Security", "security", "Safety, theft and harassment reports"),
    ("Health Services", "health-services", "Clinic and medical matters"),
    ("Library", "library", "Library services and access"),
    ("Works and Maintenance", "works", "Water, electricity and buildings"),
)
