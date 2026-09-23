"""Per-institution email templates.

Templates are not hardcoded. Each institution can define its own
branding, sender name, footer and the wording for every event that
produces an email. Variables are injected at render time:

    {{institution_name}}  Federal University Wukari
    {{institution_code}}  FUW
    {{institution_short_name}}  FUW
    {{ticket_number}}  FUW-7K2M-4318
    {{complaint_title}}  Missing result for CSC 201
    {{student_name}}  Amina Bello
    {{officer_name}}  John Musa
    {{deadline}}  24 May 2026, 5:00 PM
    {{category}}  Missing Result
    {{priority}}  high
    {{status}}  acknowledged
    {{app_url}}  https://resolve.example.com
    {{sender_name}}  FUW Resolve

If a template does not exist for an institution+event, the built-in
default for that event is used. Rendering is deliberately simple –
double-curly substitution – so an administrator cannot inject code
and a malformed template fails safely rather than executing.
"""

import re

from app.extensions import db
from app.models.base import TimestampMixin, fk, new_uuid

# Events that can trigger an email. Kept in one place so the UI can
# list them and the service can fall back to a default.
EMAIL_EVENTS = (
    "verification",          # email confirmation link
    "password_reset",        # forgot password
    "password_changed",      # password was changed
    "complaint_submitted",   # student filed
    "complaint_acknowledged",
    "complaint_in_progress",
    "complaint_awaiting_student",
    "complaint_resolved",
    "complaint_closed",
    "complaint_declined",
    "complaint_escalation",
    "assignment",            # complaint assigned to officer
    "response",              # new response on thread
    "ignored_report",        # weekly report to heads
    "invitation",            # staff invitation
)

DEFAULT_TEMPLATES = {
    "verification": {
        "subject": "Confirm your email address - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Confirm your email address to start using {{institution_name}} Resolve.\n\n"
            "{{app_url}}/verify-email?token={{token}}\n\n"
            "This link expires in {{expiry_hours}} hour(s).\n\n"
            "{{footer}}"
        ),
    },
    "password_reset": {
        "subject": "Reset your password - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Use the link below to choose a new password. It expires in an hour.\n\n"
            "{{app_url}}/reset-password?token={{token}}\n\n"
            "If you did not ask for this, you can ignore this message and your password stays as it is.\n\n"
            "{{footer}}"
        ),
    },
    "password_changed": {
        "subject": "Your password was changed - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your password has just been changed. If this was not you, contact {{institution_name}} immediately.\n\n"
            "{{footer}}"
        ),
    },
    "complaint_submitted": {
        "subject": "{{ticket_number}} received - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "We received your complaint {{ticket_number}}: \"{{complaint_title}}\".\n"
            "Category: {{category}} | Priority: {{priority}}\n"
            "Assigned to: {{officer_name}} ({{department}})\n"
            "Deadline: {{deadline}}\n\n"
            "Sign in to track progress: {{app_url}}\n\n"
            "{{footer}}"
        ),
    },
    "complaint_acknowledged": {
        "subject": "{{ticket_number}} acknowledged - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your complaint {{ticket_number}} has been acknowledged by {{officer_name}}.\n"
            "We are looking into it. Deadline: {{deadline}}\n\n"
            "{{app_url}}/complaints/{{ticket_number}}\n\n"
            "{{footer}}"
        ),
    },
    "complaint_in_progress": {
        "subject": "{{ticket_number}} in progress - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your complaint {{ticket_number}} is now in progress. {{officer_name}} is handling it.\n\n"
            "{{footer}}"
        ),
    },
    "complaint_awaiting_student": {
        "subject": "{{ticket_number}} needs your response - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "{{officer_name}} needs more information on {{ticket_number}}: {{message}}\n\n"
            "Please respond at {{app_url}}/complaints/{{ticket_number}}\n\n"
            "{{footer}}"
        ),
    },
    "complaint_resolved": {
        "subject": "{{ticket_number}} resolved - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your complaint {{ticket_number}} has been marked as resolved.\n"
            "Resolution: {{message}}\n\n"
            "If this does not resolve your issue, you can reopen it from the portal.\n\n"
            "{{footer}}"
        ),
    },
    "complaint_closed": {
        "subject": "{{ticket_number}} closed - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your complaint {{ticket_number}} is now closed. Thank you for using {{institution_name}} Resolve.\n\n"
            "{{footer}}"
        ),
    },
    "complaint_declined": {
        "subject": "{{ticket_number}} declined - {{institution_name}}",
        "body": (
            "Hello {{student_name}},\n\n"
            "Your complaint {{ticket_number}} was declined. Reason: {{message}}\n\n"
            "{{footer}}"
        ),
    },
    "complaint_escalation": {
        "subject": "{{ticket_number}} escalated - {{institution_name}}",
        "body": (
            "Hello {{officer_name}},\n\n"
            "Complaint {{ticket_number}} ({{category}}, {{priority}}) has been escalated to your unit after missing its deadline.\n"
            "Student: {{student_name}} | Filed: {{created_at}} | Deadline was: {{deadline}}\n\n"
            "{{app_url}}/complaints/{{ticket_number}}\n\n"
            "{{footer}}"
        ),
    },
    "assignment": {
        "subject": "New assignment {{ticket_number}} - {{institution_name}}",
        "body": (
            "Hello {{officer_name}},\n\n"
            "Complaint {{ticket_number}} has been assigned to you.\n"
            "Title: {{complaint_title}} | Category: {{category}} | Priority: {{priority}}\n"
            "Deadline: {{deadline}}\n\n"
            "{{app_url}}/complaints/{{ticket_number}}\n\n"
            "{{footer}}"
        ),
    },
    "response": {
        "subject": "New update on {{ticket_number}} - {{institution_name}}",
        "body": (
            "Hello {{recipient_name}},\n\n"
            "{{author_name}} responded to {{ticket_number}}:\n\n"
            "{{message}}\n\n"
            "View the thread: {{app_url}}/complaints/{{ticket_number}}\n\n"
            "{{footer}}"
        ),
    },
    "ignored_report": {
        "subject": "{{count}} complaint(s) still unanswered at {{institution_name}}",
        "body": (
            "{{count}} complaint(s) at {{institution_name}} have been escalated and are still unanswered after {{days}} days.\n\n"
            "{{complaint_list}}\n\n"
            "Each one is a student still waiting. Sign in to Resolve to see the detail: {{app_url}}\n\n"
            "{{footer}}"
        ),
    },
    "invitation": {
        "subject": "You are invited to {{institution_name}} Resolve",
        "body": (
            "Hello {{recipient_name}},\n\n"
            "You have been invited to join {{institution_name}} Resolve as {{role}}.\n"
            "Accept here: {{app_url}}/invite?token={{token}}\n\n"
            "{{footer}}"
        ),
    },
}

# Matches {{variable_name}} – letters, numbers, underscore
VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


class EmailTemplate(TimestampMixin, db.Model):
    __tablename__ = "email_templates"
    __table_args__ = (
        db.UniqueConstraint("institution_id", "event_type", name="uq_email_template_per_institution_event"),
    )

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    institution_id = db.Column(
        db.String(36), db.ForeignKey(fk("institutions.id"), ondelete="CASCADE"), nullable=False, index=True
    )

    event_type = db.Column(db.String(40), nullable=False, index=True)
    subject_template = db.Column(db.String(300), nullable=False)
    body_template = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    institution = db.relationship("Institution", backref=db.backref("email_templates", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "institution_id": self.institution_id,
            "event_type": self.event_type,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.event_type} for {self.institution_id[:8]}>"


def render_template_string(template: str, variables: dict) -> str:
    """Render a template string with {{var}} substitution.

    Missing variables are left as empty string rather than raising,
    so a template typo does not break delivery.
    """

    def replace(match):
        key = match.group(1)
        value = variables.get(key)
        if value is None:
            return ""
        return str(value)

    return VARIABLE_RE.sub(replace, template)


def get_default_template(event_type: str) -> dict:
    return DEFAULT_TEMPLATES.get(event_type, DEFAULT_TEMPLATES["response"])
