"""Importing the student register.

Admissions happen every session, so this is not a one-off load. Each
import is tied to a session and adds to the register rather than
replacing it: a returning student keeps their record and their history,
a new intake is added, and nobody is quietly deleted because they were
missing from one spreadsheet.

Supports both CSV and XLSX (openpyxl). Matric format is not hardcoded:
each institution defines its own pattern (e.g. FUW: eng/coe/21/013
=> faculty_code/dept_code/year/number). Validation uses the
institution's matric_pattern regex when present, case-insensitive.

Archive: when Cloudinary is enabled (free tier 25GB), the raw uploaded
file is stored as authenticated raw asset under registers/{institution}/
so Render's ephemeral filesystem does not lose it.
"""

import csv
import io
import re
import secrets
from datetime import datetime

from app.extensions import db
from app.models.academic import AcademicDepartment, AcademicSession, Faculty, StudentRecord

REQUIRED_COLUMNS = ("matric_number", "full_name")
OPTIONAL_COLUMNS = ("faculty", "department", "programme", "level", "status", "faculty_code", "department_code", "entry_year", "email")

MAX_ROWS = 20000


def normalise_matric(value: str) -> str:
    """Reduce a matriculation number to a comparable form.

    Formats differ widely between institutions, and the same number is
    written inconsistently even within one. Comparing a normalised form
    avoids rejecting a student over a separator.

    FUW format: eng/coe/21/013 => normalised to ENG/COE/21/013
    """
    cleaned = re.sub(r"[\s\-_/\\\.]+", "/", (value or "").strip().upper())
    return cleaned.strip("/")


def compile_matric_pattern(pattern: str | None):
    """Compile institution matric pattern, case-insensitive."""
    if not pattern:
        return None
    try:
        # Ensure pattern is anchored? We respect as given, but compile IGNORECASE
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None


def validate_matric_against_pattern(matric: str, institution) -> tuple[bool, str | None]:
    """Validate matric against institution's pattern if defined.

    Returns (is_valid, error_message)
    """
    if not institution:
        return True, None
    pattern_str = getattr(institution, "matric_pattern", None)
    if not pattern_str:
        return True, None

    compiled = compile_matric_pattern(pattern_str)
    if not compiled:
        # Invalid regex in DB – don't block, but log
        return True, None

    # Test against both raw and normalised (uppercased) forms
    if compiled.match(matric) or compiled.match(normalise_matric(matric)):
        return True, None

    example = getattr(institution, "matric_example", None) or "ENG/COE/21/013"
    desc = getattr(institution, "matric_format_description", None) or ""
    msg = f"Matric '{matric}' does not match {institution.code} format. Expected like {example}"
    if desc:
        msg += f" ({desc})"
    return False, msg


def parse_csv(payload: bytes) -> tuple[list[dict], list[str]]:
    """Read CSV payload, reporting problems rather than guessing."""
    problems: list[str] = []

    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
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

        matric_raw = row.get("matric_number", "")
        matric = normalise_matric(matric_raw)
        name = row.get("full_name", "")

        if not matric or not name:
            problems.append(f"Row {number}: matric number and name are both required.")
            continue

        level = row.get("level", "")
        rows.append(
            {
                "matric_number": matric,
                "matric_raw": matric_raw,
                "full_name": name[:150],
                "faculty": row.get("faculty", ""),
                "faculty_code": row.get("faculty_code", ""),
                "department": row.get("department", ""),
                "department_code": row.get("department_code", ""),
                "programme": row.get("programme", "")[:150] or None,
                "level": int(level) if str(level).isdigit() else None,
                "status": (row.get("status") or "active").lower(),
                "email": row.get("email", "") or row.get("institution_email", ""),
                "row": number,
            }
        )

        if len(rows) > MAX_ROWS:
            problems.append(
                f"Only the first {MAX_ROWS} rows were read. Split the file and import again."
            )
            break

    return rows, problems


def parse_xlsx(payload: bytes) -> tuple[list[dict], list[str]]:
    """Read the first workbook sheet containing the register columns.

    An institution's workbook commonly contains several sheets: branding,
    faculties, departments, offices, and finally the student register. The
    active sheet is not a reliable choice, so locate the sheet by its
    required headers instead of silently rejecting a valid workbook.
    """
    problems: list[str] = []
    try:
        import openpyxl
    except ImportError:
        return [], ["XLSX support requires openpyxl. Install it or upload CSV."]

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
        selected_rows = None
        selected_headers = None

        for ws in wb.worksheets:
            rows_iter = ws.iter_rows(values_only=True)
            try:
                header_row = next(rows_iter)
            except StopIteration:
                continue
            if not header_row:
                continue

            headers = [
                str(value).strip().lower().replace(" ", "_") if value is not None else ""
                for value in header_row
            ]
            if set(REQUIRED_COLUMNS).issubset(headers):
                selected_headers = headers
                selected_rows = rows_iter
                break

        if selected_rows is None or selected_headers is None:
            required = " and a ".join(REQUIRED_COLUMNS)
            return [], [f"The workbook needs a sheet containing a {required} column."]

        rows = []
        for number, raw_values in enumerate(selected_rows, start=2):
            if raw_values is None:
                continue

            row = {}
            for index, header in enumerate(selected_headers):
                value = raw_values[index] if index < len(raw_values) else None
                row[header] = "" if value is None else str(value).strip()

            matric_raw = row.get("matric_number", "")
            matric = normalise_matric(matric_raw)
            name = row.get("full_name", "")

            if not matric and not name:
                continue
            if not matric or not name:
                problems.append(f"Row {number}: matric number and name are both required.")
                continue

            level = row.get("level", "")
            rows.append(
                {
                    "matric_number": matric,
                    "matric_raw": matric_raw,
                    "full_name": name[:150],
                    "faculty": row.get("faculty", ""),
                    "faculty_code": row.get("faculty_code", ""),
                    "department": row.get("department", ""),
                    "department_code": row.get("department_code", ""),
                    "programme": row.get("programme", "")[:150] or None,
                    "level": int(float(level)) if str(level).replace(".", "", 1).isdigit() else None,
                    "status": (row.get("status") or "active").lower(),
                    "email": row.get("email", "") or row.get("institution_email", ""),
                    "row": number,
                }
            )

            if len(rows) > MAX_ROWS:
                problems.append(
                    f"Only the first {MAX_ROWS} rows were read. Split the file and import again."
                )
                break

        return rows, problems

    except Exception as e:
        return [], [f"We could not read that Excel file: {str(e)[:200]}. Save as CSV and try again."]


def parse_register_file(payload: bytes, filename: str = "") -> tuple[list[dict], list[str], str]:
    """Detect file type and parse.

    Returns (rows, problems, detected_type)
    """
    name_lower = (filename or "").lower()
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        rows, problems = parse_xlsx(payload)
        return rows, problems, "xlsx"
    # Try to detect XLSX by magic number (PK zip)
    if payload[:2] == b"PK":
        # Could be XLSX
        rows, problems = parse_xlsx(payload)
        if rows or not problems or "openpyxl" not in problems[0]:
            return rows, problems, "xlsx"
        # Fall through to CSV if XLSX parse failed due to missing lib
    rows, problems = parse_csv(payload)
    return rows, problems, "csv"


def archive_register_file(institution, payload: bytes, original_filename: str, content_type: str = "") -> tuple[str, str]:
    """Archive the uploaded register file to Cloudinary if enabled, else local.

    Returns (stored_name, backend_name)
    """
    from app.services import storage as storage_service
    from app.services.storage import backend_name, write_bytes

    # Generate stored name: registers/{institution_code}/{timestamp}_{random}_{original}
    safe_name = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in (original_filename or "register.csv"))[-100:]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(4)
    code = getattr(institution, "code", "UNK")[:10]
    stored_name = f"registers/{code}/{timestamp}_{rand}_{safe_name}"

    # Ensure content type
    if not content_type:
        if safe_name.lower().endswith(".xlsx"):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif safe_name.lower().endswith(".csv"):
            content_type = "text/csv"
        else:
            content_type = "application/octet-stream"

    try:
        write_bytes(stored_name, payload, content_type)
        backend = backend_name()
    except Exception:
        # Fallback: try local write directly
        from app.services.storage import upload_root
        try:
            root = upload_root()
            (root / stored_name).parent.mkdir(parents=True, exist_ok=True)
            (root / stored_name).write_bytes(payload)
            backend = "local"
        except Exception:
            # If even local fails, return empty
            return "", "local"

    return stored_name, backend


def import_register(institution, session: AcademicSession, payload: bytes,
                    dry_run: bool = False, filename: str = "", uploaded_by=None) -> dict:
    """Load a register for one session.

    Runs as a dry run first by default in the interface, because an
    administrator should see what a file will do before it does it.

    Now supports CSV and XLSX, validates against institution's
    matric_pattern, and archives the file to Cloudinary when available.
    """
    rows, problems, detected_type = parse_register_file(payload, filename)

    summary = {
        "session": session.name,
        "rows_read": len(rows),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "problems": problems[:50],
        "dry_run": dry_run,
        "detected_type": detected_type,
        "matric_pattern": getattr(institution, "matric_pattern", None),
        "matric_example": getattr(institution, "matric_example", None),
    }

    # Validate matric pattern per row if institution has pattern
    if institution and getattr(institution, "matric_pattern", None):
        pattern = compile_matric_pattern(institution.matric_pattern)
        if pattern:
            for row in rows[:]:
                # Use raw and normalised
                if not pattern.match(row["matric_number"]) and not pattern.match(row.get("matric_raw", "")):
                    # Try case-insensitive already via compile, but also test lower
                    # If still fails, add problem
                    summary["problems"].append(
                        f"Row {row['row']}: matric '{row.get('matric_raw') or row['matric_number']}' does not match {institution.code} format {institution.matric_pattern} (example {institution.matric_example})."
                    )

    if not rows:
        return summary

    faculties_by_name = {
        f.name.strip().lower(): f
        for f in Faculty.query.filter_by(institution_id=institution.id).all()
    }
    faculties_by_code = {
        (f.code or "").strip().lower(): f
        for f in Faculty.query.filter_by(institution_id=institution.id).all()
        if f.code
    }
    faculties_by_slug = {
        f.slug.strip().lower(): f
        for f in Faculty.query.filter_by(institution_id=institution.id).all()
    }

    departments_by_name = {
        d.name.strip().lower(): d
        for d in AcademicDepartment.query.filter_by(institution_id=institution.id).all()
    }
    departments_by_code = {
        (d.code or "").strip().lower(): d
        for d in AcademicDepartment.query.filter_by(institution_id=institution.id).all()
        if d.code
    }
    departments_by_slug = {
        d.slug.strip().lower(): d
        for d in AcademicDepartment.query.filter_by(institution_id=institution.id).all()
    }

    existing = {
        r.matric_number: r
        for r in StudentRecord.query.filter_by(institution_id=institution.id).all()
    }

    def find_faculty(row):
        # Try by code first (for FUW format eng/coe/21/013)
        if row.get("faculty_code"):
            fc = row["faculty_code"].strip().lower()
            if fc in faculties_by_code:
                return faculties_by_code[fc]
            if fc in faculties_by_slug:
                return faculties_by_slug[fc]
        if row.get("faculty"):
            name = row["faculty"].strip().lower()
            if name in faculties_by_name:
                return faculties_by_name[name]
            if name in faculties_by_code:
                return faculties_by_code[name]
        # Try parsing matric: first part is faculty code
        matric = row.get("matric_number", "")
        if "/" in matric:
            parts = matric.split("/")
            if parts:
                maybe_fac = parts[0].strip().lower()
                if maybe_fac in faculties_by_code:
                    return faculties_by_code[maybe_fac]
                if maybe_fac in faculties_by_slug:
                    return faculties_by_slug[maybe_fac]
        return None

    def find_department(row):
        if row.get("department_code"):
            dc = row["department_code"].strip().lower()
            if dc in departments_by_code:
                return departments_by_code[dc]
            if dc in departments_by_slug:
                return departments_by_slug[dc]
        if row.get("department"):
            name = row["department"].strip().lower()
            if name in departments_by_name:
                return departments_by_name[name]
            if name in departments_by_code:
                return departments_by_code[name]
        # Parse matric second part
        matric = row.get("matric_number", "")
        if "/" in matric:
            parts = matric.split("/")
            if len(parts) >= 2:
                maybe_dept = parts[1].strip().lower()
                if maybe_dept in departments_by_code:
                    return departments_by_code[maybe_dept]
                if maybe_dept in departments_by_slug:
                    return departments_by_slug[maybe_dept]
        return None

    for row in rows:
        faculty = find_faculty(row)
        department = find_department(row)

        if row.get("faculty") and not faculty and not row.get("faculty_code"):
            # Only warn if faculty name given but not found; if code parsing, silent
            if row["faculty"].strip().lower() not in faculties_by_code:
                summary["problems"].append(
                    f"Row {row['row']}: no faculty named '{row['faculty']}'. Create it first, or leave blank."
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

        # Returning student
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

    # Archive file if not dry_run
    stored_name = ""
    backend = "local"
    if not dry_run:
        try:
            stored_name, backend = archive_register_file(
                institution, payload, filename or f"register_{session.name}.{detected_type}",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if detected_type == "xlsx" else "text/csv"
            )
        except Exception:
            stored_name, backend = "", "local"

        # Record import history
        try:
            from app.models.register_import import RegisterImport
            imp = RegisterImport(
                institution_id=institution.id,
                session_id=session.id,
                uploaded_by_user_id=getattr(uploaded_by, "id", None),
                original_filename=filename or f"register_{session.name}.{detected_type}",
                stored_name=stored_name or f"registers/{institution.code}/{secrets.token_hex(8)}",
                storage_backend=backend,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if detected_type == "xlsx" else "text/csv",
                size_bytes=len(payload),
                rows_read=summary["rows_read"],
                created_count=summary["created"],
                updated_count=summary["updated"],
                skipped_count=summary["skipped"],
                problems_json=summary["problems"][:20],
                dry_run=False,
            )
            db.session.add(imp)
        except Exception:
            pass

        db.session.commit()
    else:
        # For dry run, don't archive, but show what would happen
        summary["archive_would_be"] = f"registers/{institution.code}/..."

    summary["problems"] = summary["problems"][:50]
    summary["stored_name"] = stored_name
    summary["storage_backend"] = backend
    return summary


def find_for_registration(institution, matric_number: str) -> StudentRecord | None:
    """Look up a register entry during sign-up."""
    return StudentRecord.query.filter_by(
        institution_id=institution.id,
        matric_number=normalise_matric(matric_number),
    ).first()
