"""Email templating – not hardcoded, per-institution.

Each institution can define templates for every email event. Variables
are injected at render time: ticket, deadline, officer, etc. If no
custom template exists, the built-in default for that event is used.

Rendering uses {{var}} substitution (safe, no code execution).
"""

import re
from datetime import datetime

from flask import current_app

from app.models.email_template import DEFAULT_TEMPLATES, EmailTemplate, render_template_string

# Re-export for convenience
VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _institution_vars(institution) -> dict:
    if not institution:
        return {}
    return {
        "institution_name": institution.name,
        "institution_code": institution.code,
        "institution_short_name": institution.short_name or institution.code,
        "institution_slug": institution.slug,
        "sender_name": institution.email_sender_name or f"{institution.short_name or institution.code} Resolve",
        "footer": institution.email_footer or (
            f"{institution.name} - Complaint Resolution System\n"
            "This is an automated message, please do not reply directly."
        ),
        "app_url": current_app.config.get("APP_URL", "").rstrip("/") or "https://uni-complaints.vercel.app",
    }


def _format_deadline(dt) -> str:
    if not dt:
        return ""
    try:
        # Ensure aware
        if hasattr(dt, "strftime"):
            return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        pass
    return str(dt)


def build_variables(institution, **extra) -> dict:
    """Merge institution defaults + caller supplied variables + footer alias."""
    vars_ = {}
    vars_.update(_institution_vars(institution))
    # Extra overrides
    for k, v in extra.items():
        if v is None:
            continue
        # Format datetime objects for deadline-like fields
        if k in ("deadline", "created_at", "resolve_due_at", "acknowledge_due_at") and hasattr(v, "strftime"):
            vars_[k] = _format_deadline(v)
        else:
            vars_[k] = v

    # Alias footer as {{footer}} and {{email_footer}}
    if "footer" in vars_:
        vars_["email_footer"] = vars_["footer"]
    # Ensure app_url always present
    if "app_url" not in vars_:
        vars_["app_url"] = current_app.config.get("APP_URL", "").rstrip("/") or "https://uni-complaints.vercel.app"

    # Common aliases
    if "student_name" not in vars_ and "recipient_name" in vars_:
        vars_["student_name"] = vars_["recipient_name"]
    if "recipient_name" not in vars_ and "student_name" in vars_:
        vars_["recipient_name"] = vars_["student_name"]

    return vars_


def get_template(institution, event_type: str):
    """Return EmailTemplate row if exists and active, else None."""
    if not institution:
        return None
    try:
        return EmailTemplate.query.filter_by(
            institution_id=institution.id, event_type=event_type, is_active=True
        ).first()
    except Exception:
        return None


def render_event(institution, event_type: str, variables: dict) -> tuple[str, str]:
    """Render subject and body for an event.

    Returns (subject, body). Always returns something – falls back to default.
    """
    template_row = get_template(institution, event_type)
    if template_row:
        subject_tpl = template_row.subject_template
        body_tpl = template_row.body_template
    else:
        defaults = DEFAULT_TEMPLATES.get(event_type, DEFAULT_TEMPLATES["response"])
        subject_tpl = defaults["subject"]
        body_tpl = defaults["body"]

    merged_vars = build_variables(institution, **variables)

    subject = render_template_string(subject_tpl, merged_vars)
    body = render_template_string(body_tpl, merged_vars)

    # Prepend sender name to subject if institution has branding? No – subject already includes institution.
    # Ensure footer placeholder resolved
    return subject, body


def queue_templated_email(institution, to_address: str, event_type: str, variables: dict,
                          user_id: str | None = None, complaint_id: str | None = None):
    """Queue an email using the templating system.

    This is the replacement for direct queue_email calls with hardcoded strings.
    """
    from app.services.delivery import queue_email

    subject, body = render_event(institution, event_type, variables)
    return queue_email(
        institution.id if institution else None,
        to_address,
        subject,
        body,
        user_id=user_id,
        complaint_id=complaint_id,
    )
