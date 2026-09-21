"""Importing the student register.

Admissions happen every session, so this is not a one-off load. Each
import is tied to a session and adds to the register rather than
replacing it: a returning student keeps their record and their history,
a new intake is added, and nobody is quietly deleted because they were
missing from one spreadsheet.
"""

import csv
import io
import re

from app.extensions import db
from app.models.academic import AcademicDepartment, AcademicSession, Faculty, StudentRecord

REQUIRED_COLUMNS = ("matric_number", "full_name")
OPTIONAL_COLUMNS = ("faculty", "department", "programme", "level", "status")

MAX_ROWS = 20000


def normalise_matric(value: str) -> str:
    """Reduce a matriculation number to a comparable form.

    Formats differ widely between institutions, and the same number is
    written inconsistently even within one. Comparing a normalised form
    avoids rejecting a student over a separator.
    """
    cleaned = re.sub(r"[\s\-_/\\.]+", "/", (value or "").strip().upper())
    return cleaned.strip("/")


def parse_csv(payload: bytes) -> tuple[list[dict], list[str]]:
    """Read the spreadsheet, reporting problems rather than guessing."""
    problems: list[str] = []

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            # Spreadsheets exported on Windows are often not UTF-8.
            text = payload.decode("latin-1")
        except UnicodeDecodeError:
            return [], ["We could not read that file. Save it as CSV and try again."]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["That file appears to be empty."]

    headers = {(h or "").strip().lower().replace(" ", "_") for h in reader.fieldnames}
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        return [], [f"The file needs a {' and a '.join(missing)} column."]

    rows = []
    for number, raw in enumerate(reader, start=2):
        row = {
            (k or "").strip().lower().replace(" ", "_"): (v or "").strip()
            for k, v in raw.items()
        }

        matric = normalise_matric(row.get("matric_number", ""))
        name = row.get("full_name", "")

        if not matric or not name:
            problems.append(f"Row {number}: matric number and name are both required.")
            continue

        level = row.get("level", "")
        rows.append(
            {
                "matric_number": matric,
                "full_name": name[:150],
                "faculty": row.get("faculty", ""),
                "department": row.get("department", ""),
                "programme": row.get("programme", "")[:150] or None,
                "level": int(level) if level.isdigit() else None,
                "status": (row.get("status") or "active").lower(),
                "row": number,
            }
        )

        if len(rows) > MAX_ROWS:
            problems.append(
                f"Only the first {MAX_ROWS} rows were read. Split the file and import again."
            )
            break

    return rows, problems


def import_register(institution, session: AcademicSession, payload: bytes,
                    dry_run: bool = False) -> dict:
    """Load a register for one session.

    Runs as a dry run first by default in the interface, because an
    administrator should see what a file will do before it does it.
    """
    rows, problems = parse_csv(payload)
    summary = {
        "session": session.name,
        "rows_read": len(rows),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "problems": problems[:50],
        "dry_run": dry_run,
    }

    if not rows:
        return summary

    faculties = {
        f.name.strip().lower(): f
        for f in Faculty.query.filter_by(institution_id=institution.id).all()
    }
    departments = {
        d.name.strip().lower(): d
        for d in AcademicDepartment.query.filter_by(institution_id=institution.id).all()
    }
    existing = {
        r.matric_number: r
        for r in StudentRecord.query.filter_by(institution_id=institution.id).all()
    }

    for row in rows:
        faculty = faculties.get(row["faculty"].strip().lower()) if row["faculty"] else None
        department = (
            departments.get(row["department"].strip().lower()) if row["department"] else None
        )

        if row["faculty"] and not faculty:
            summary["problems"].append(
                f"Row {row['row']}: no faculty named '{row['faculty']}'. "
                "Create it first, or leave the column blank."
            )

        record = existing.get(row["matric_number"])

        if record is None:
            if not dry_run:
                db.session.add(
                    StudentRecord(
                        institution_id=institution.id,
                        matric_number=row["matric_number"],
                        full_name=row["full_name"],
                        faculty_id=faculty.id if faculty else None,
                        academic_department_id=department.id if department else None,
                        programme=row["programme"],
                        level=row["level"],
                        status=row["status"],
                        admitted_session_id=session.id,
                    )
                )
            summary["created"] += 1
            continue

        # A returning student. Their progression is updated, but the
        # record is never reassigned: if someone has already registered
        # against it, that link stands.
        changed = False
        for field, value in (
            ("full_name", row["full_name"]),
            ("programme", row["programme"]),
            ("level", row["level"]),
            ("status", row["status"]),
        ):
            if value and getattr(record, field) != value:
                if not dry_run:
                    setattr(record, field, value)
                changed = True

        if faculty and record.faculty_id != faculty.id:
            if not dry_run:
                record.faculty_id = faculty.id
            changed = True
        if department and record.academic_department_id != department.id:
            if not dry_run:
                record.academic_department_id = department.id
            changed = True

        summary["updated" if changed else "skipped"] += 1

    if not dry_run:
        db.session.commit()

    summary["problems"] = summary["problems"][:50]
    return summary


def find_for_registration(institution, matric_number: str) -> StudentRecord | None:
    """Look up a register entry during sign-up."""
    return StudentRecord.query.filter_by(
        institution_id=institution.id,
        matric_number=normalise_matric(matric_number),
    ).first()
