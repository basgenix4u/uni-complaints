"""Per-institution email template management.

Templates are not hardcoded. Each institution defines its own branding
and wording for every email event, with variables like ticket, deadline,
officer, etc.

Free tier: no extra cost, templates stored in DB, rendered with safe
{{var}} substitution.
"""

from flask import Blueprint, g, request

from app.extensions import db
from app.models.email_template import DEFAULT_TEMPLATES, EMAIL_EVENTS, EmailTemplate
from app.models.institution import Institution
from app.routes.auth import fail, ok
from app.security import staff_required, tenant_query

bp = Blueprint("email_templates", __name__, url_prefix="/api/email-templates")


@bp.get("")
@staff_required("institution_admin")
def list_templates():
    """List all templates for current institution, merged with defaults."""
    institution = db.session.get(Institution, g.institution_id)
    existing = {
        t.event_type: t
        for t in tenant_query(EmailTemplate).all()
    }

    payload = []
    for event in EMAIL_EVENTS:
        row = existing.get(event)
        if row:
            data = row.to_dict()
            data["is_custom"] = True
            data["default_subject"] = DEFAULT_TEMPLATES.get(event, {}).get("subject", "")
            data["default_body"] = DEFAULT_TEMPLATES.get(event, {}).get("body", "")
        else:
            defaults = DEFAULT_TEMPLATES.get(event, DEFAULT_TEMPLATES["response"])
            data = {
                "event_type": event,
                "subject_template": defaults["subject"],
                "body_template": defaults["body"],
                "is_active": True,
                "is_custom": False,
                "default_subject": defaults["subject"],
                "default_body": defaults["body"],
                "institution_id": g.institution_id,
            }
        payload.append(data)

    return ok(
        {
            "templates": payload,
            "institution": {
                "email_sender_name": institution.email_sender_name,
                "email_footer": institution.email_footer,
                "email_reply_to": institution.email_reply_to,
                "matric_pattern": institution.matric_pattern,
                "matric_example": institution.matric_example,
                "matric_format_description": institution.matric_format_description,
            },
            "available_variables": [
                "institution_name", "institution_code", "institution_short_name",
                "ticket_number", "complaint_title", "category", "priority", "status",
                "student_name", "recipient_name", "officer_name", "author_name",
                "deadline", "created_at", "resolve_due_at", "department",
                "message", "app_url", "footer", "token", "link", "count",
                "complaint_list", "days", "role", "expiry_hours"
            ],
        }
    )


@bp.put("/branding")
@staff_required("institution_admin")
def update_branding():
    """Update per-institution email branding (sender name, footer, etc.)."""
    institution = db.session.get(Institution, g.institution_id)
    payload = request.get_json(silent=True) or {}

    if "email_sender_name" in payload:
        institution.email_sender_name = (payload["email_sender_name"] or "").strip()[:100] or None
    if "email_footer" in payload:
        institution.email_footer = (payload["email_footer"] or "").strip()[:1000] or None
    if "email_reply_to" in payload:
        institution.email_reply_to = (payload["email_reply_to"] or "").strip()[:255] or None
    if "matric_pattern" in payload:
        import re
        pat = (payload["matric_pattern"] or "").strip()
        if pat:
            try:
                re.compile(pat, re.IGNORECASE)
            except re.error:
                return fail("That matric pattern is not a valid regular expression.", 422,
                            {"matric_pattern": "Invalid regex."})
            institution.matric_pattern = pat
        else:
            institution.matric_pattern = None
    if "matric_example" in payload:
        institution.matric_example = (payload["matric_example"] or "").strip()[:60] or None
    if "matric_format_description" in payload:
        institution.matric_format_description = (payload["matric_format_description"] or "").strip()[:200] or None

    db.session.commit()
    return ok({"institution": institution.to_dict(include_settings=True)}, "Branding updated.")


@bp.put("/<event_type>")
@staff_required("institution_admin")
def upsert_template(event_type):
    """Create or update a template for an event."""
    event_type = (event_type or "").strip()
    if event_type not in EMAIL_EVENTS:
        return fail(f"Unknown event type. Choose from: {', '.join(EMAIL_EVENTS)}", 422)

    payload = request.get_json(silent=True) or {}
    subject = (payload.get("subject_template") or "").strip()
    body = (payload.get("body_template") or "").strip()

    if len(subject) < 5:
        return fail("Subject is too short.", 422, {"subject_template": "Enter a subject."})
    if len(body) < 10:
        return fail("Body is too short.", 422, {"body_template": "Enter a body."})

    existing = tenant_query(EmailTemplate).filter_by(event_type=event_type).first()
    if existing:
        existing.subject_template = subject[:300]
        existing.body_template = body
        existing.is_active = bool(payload.get("is_active", True))
    else:
        existing = EmailTemplate(
            institution_id=g.institution_id,
            event_type=event_type,
            subject_template=subject[:300],
            body_template=body,
            is_active=bool(payload.get("is_active", True)),
        )
        db.session.add(existing)

    db.session.commit()
    return ok({"template": existing.to_dict()}, "Template saved.")


@bp.delete("/<event_type>")
@staff_required("institution_admin")
def delete_template(event_type):
    """Delete custom template, falling back to default."""
    existing = tenant_query(EmailTemplate).filter_by(event_type=event_type).first()
    if not existing:
        return fail("No custom template for that event.", 404)
    db.session.delete(existing)
    db.session.commit()
    defaults = DEFAULT_TEMPLATES.get(event_type, DEFAULT_TEMPLATES["response"])
    return ok(
        {
            "template": {
                "event_type": event_type,
                "subject_template": defaults["subject"],
                "body_template": defaults["body"],
                "is_custom": False,
            }
        },
        "Reverted to default.",
    )


@bp.post("/preview/<event_type>")
@staff_required("institution_admin")
def preview_template(event_type):
    """Preview rendering with sample variables."""
    from app.services.email_templating import build_variables, render_template_string

    payload = request.get_json(silent=True) or {}
    subject_tpl = payload.get("subject_template") or ""
    body_tpl = payload.get("body_template") or ""

    if not subject_tpl and not body_tpl:
        # Use stored or default
        existing = tenant_query(EmailTemplate).filter_by(event_type=event_type).first()
        if existing:
            subject_tpl = existing.subject_template
            body_tpl = existing.body_template
        else:
            defaults = DEFAULT_TEMPLATES.get(event_type, DEFAULT_TEMPLATES["response"])
            subject_tpl = defaults["subject"]
            body_tpl = defaults["body"]

    institution = db.session.get(Institution, g.institution_id)

    sample_vars = {
        "institution_name": institution.name if institution else "Federal University Wukari",
        "institution_code": institution.code if institution else "FUW",
        "institution_short_name": institution.short_name or "FUW" if institution else "FUW",
        "ticket_number": "FUW-7K2M-4318",
        "complaint_title": "Missing result for CSC 201",
        "category": "Missing Result",
        "priority": "high",
        "status": "acknowledged",
        "student_name": "Amina Bello",
        "recipient_name": "Amina Bello",
        "officer_name": "John Musa",
        "author_name": "John Musa",
        "deadline": "24 May 2026, 5:00 PM",
        "created_at": "20 May 2026, 9:00 AM",
        "department": "Exams & Records",
        "message": "We have verified your result and updated the portal.",
        "app_url": "https://uni-complaints.vercel.app",
        "footer": institution.email_footer if institution and institution.email_footer else "Federal University Wukari - Resolve",
        "token": "sample-token-123",
        "link": "https://uni-complaints.vercel.app/verify?token=sample",
        "count": 5,
        "complaint_list": "FUW-001 Missing Result filed 20 May 2026\nFUW-002 Fee receipt issue filed 19 May 2026",
        "days": 7,
        "role": "officer",
        "expiry_hours": 72,
    }

    merged = build_variables(institution, **sample_vars)
    subject = render_template_string(subject_tpl, merged)
    body = render_template_string(body_tpl, merged)

    return ok({"preview": {"subject": subject, "body": body}})
