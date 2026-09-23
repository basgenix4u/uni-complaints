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

# Sensible starting policy, offered for review rather than treated as a
# universal truth. Each institution can change these under Routing. The
# resolution factor multiplies the category/unit SLA; the other figures
# are working hours.
DEFAULT_PRIORITY_POLICIES = (
    ("urgent", 1, 0.25, 2, 2),
    ("high", 4, 0.50, 8, 4),
    ("medium", 8, 1.00, 24, 12),
    ("low", 24, 2.00, 48, 24),
)


class PriorityPolicy(TimestampMixin, db.Model):
    """How quickly one institution treats a complaint at this priority.

    Priority behaviour used to be half data and half constants: the
    resolution target changed, acknowledgement never did, and every
    rung of escalation got the same day regardless of urgency. Keeping
    the four figures together makes the policy visible, tenant-specific
    and measurable.
    """

    __tablename__ = "priority_policies"
    __table_args__ = (
        db.UniqueConstraint(
            "institution_id", "priority", name="uq_priority_policy_institution_priority"
        ),
        db.Index("ix_priority_policy_institution", "institution_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36),
        db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"),
        nullable=False,
    )
    priority = db.Column(db.String(20), nullable=False)
    acknowledge_hours = db.Column(db.Integer, nullable=False)
    resolution_factor = db.Column(db.Float, nullable=False)
    escalation_step_hours = db.Column(db.Integer, nullable=False)
    reminder_hours_before_due = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "priority": self.priority,
            "acknowledge_hours": self.acknowledge_hours,
            "resolution_factor": self.resolution_factor,
            "escalation_step_hours": self.escalation_step_hours,
            "reminder_hours_before_due": self.reminder_hours_before_due,
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
    ("transcript", "registry", "unit", None, False),
    ("certificate", "registry", "unit", None, False),
    ("id_card", "registry", "unit", None, False),
    ("clearance", "registry", "unit", None, False),
    ("admission", "admissions", "unit", "registry", False),
    ("registration", "registry", "unit", None, False),
    ("transfer", "registry", "unit", None, False),
    ("fees_payment", "bursary", "unit", None, False),
    ("scholarship", "bursary", "unit", "student-affairs", False),
    ("accommodation", "student-affairs", "unit", None, False),
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
    ("Student Affairs", "student-affairs", "Hostel, welfare, discipline and student union"),
    ("ICT", "ict", "Portal, email and network faults"),
    ("Security", "security", "Safety, theft and harassment reports"),
    ("Health Services", "health-services", "Clinic and medical matters"),
    ("Library", "library", "Library services and access"),
    ("Works and Maintenance", "works", "Water, electricity and buildings"),
)
