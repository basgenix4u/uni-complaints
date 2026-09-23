#!/usr/bin/env python3
"""
Register Federal University Wukari (FUW) as test institution live,
for research pilot.

Uses platform admin token to POST /api/platform/institutions with:
- matric_pattern = ^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$  (eng/coe/21/013)
- matric_example = eng/coe/21/013
- matric_format_description = faculty_code/dept_code/year/number
- email branding per institution (not hardcoded)

Then:
- Create session 2023/2024 current
- Import structure from Excel (Faculties + Departments sheets)
- Import Offices as departments
- Import Students_300 via XLSX (CSV+XLSX support, Cloudinary archive)

After pilot: delete pilot data and re-register clean for production.

Usage:
  export API_URL=https://resolve-api-eadv.onrender.com
  export PLATFORM_TOKEN=your_jwt
  python scripts/register_fuw_pilot.py

Free tier: stays on Render free + Cloudinary free 25GB.
"""

import os
import sys
import json
import requests
import openpyxl
from pathlib import Path

API_URL = os.getenv("API_URL", "https://resolve-api-eadv.onrender.com").rstrip("/")
TOKEN = os.getenv("PLATFORM_TOKEN") or os.getenv("TOKEN")
EXCEL_PATH = Path(__file__).parent.parent / "docs" / "FUW_Pilot_Dataset_300_Students.xlsx"

if not TOKEN:
    print("Set PLATFORM_TOKEN env var (platform_admin JWT)")
    sys.exit(1)

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, payload):
    url = f"{API_URL}{path}"
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"POST {path} -> {r.status_code}")
    try:
        data = r.json()
        print(json.dumps(data, indent=2)[:2000])
    except:
        print(r.text[:1000])
    return r

def get(path, params=None):
    url = f"{API_URL}{path}"
    r = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"GET {path} -> {r.status_code}")
    return r

# 1. Register FUW
fuw_payload = {
    "name": "Federal University Wukari",
    "code": "FUW",
    "slug": "federal-university-wukari",
    "short_name": "FUW",
    "type": "university",
    "state": "Taraba",
    "ownership": "federal",
    "contact_email": "info@fuwukari.edu.ng",
    "contact_phone": "+234",
    "verification_mode": "register",
    "is_onboarded": True,
    "allow_anonymous": False,
    "matric_pattern": r"^[a-z]{3}/[a-z]{3}/[0-9]{2}/[0-9]{3}$",
    "matric_example": "eng/coe/21/013",
    "matric_format_description": "faculty_code/dept_code/year/number e.g. eng=Engineering, coe=Computer Engineering, 21=2021 entry, 013=student number",
    "email_sender_name": "FUW Resolve",
    "email_footer": "Federal University Wukari - Student Complaint Resolution System\nThis is an automated message, please do not reply directly. Sign in at https://uni-complaints.vercel.app",
    "email_reply_to": "complaints@fuwukari.edu.ng",
    "admin_email": "admin@fuwukari.edu.ng",
    "admin_name": "FUW Admin",
    "admin_password": "FUWAdmin123!",
}

print("\n=== 1. Register FUW Institution ===")
r = post("/api/platform/institutions", fuw_payload)
if r.status_code == 409:
    print("FUW already exists, trying to onboard existing...")
    # Try to find existing FUW
    existing = get("/api/platform/institutions", {"scope": "directory", "q": "Wukari"})
    try:
        data = existing.json()
        insts = data.get("data", {}).get("institutions", [])
        for inst in insts:
            if inst["code"] == "FUW" or "Wukari" in inst["name"]:
                print(f"Found {inst['name']} {inst['id']} onboarded={inst['is_onboarded']}")
                if not inst["is_onboarded"]:
                    onboard = post(f"/api/platform/institutions/{inst['id']}/onboard", {
                        "admin_email": "admin@fuwukari.edu.ng",
                        "admin_name": "FUW Admin",
                        "admin_password": "FUWAdmin123!",
                        "verification_mode": "register",
                        "allow_anonymous": False,
                    })
    except Exception as e:
        print(f"Error finding existing: {e}")

# 2. Instructions for manual steps (need institution_admin token for academic imports)
print("\n=== 2. Next steps (need institution_admin token) ===")
print("""
After FUW is created, sign in as admin@fuwukari.edu.ng to get institution token:

  curl -X POST $API_URL/api/auth/login -H "Content-Type: application/json" \\
    -d '{"email":"admin@fuwukari.edu.ng","password":"FUWAdmin123!","institution":"federal-university-wukari"}'

Then:

  # Create session 2023/2024 current
  curl -X POST $API_URL/api/academic/sessions -H "Authorization: Bearer <INST_TOKEN>" \\
    -H "Content-Type: application/json" -d '{"name":"2023/2024","is_current":true}'

  # Import Faculties/Departments from Excel sheet Departments
  # Convert Departments sheet to CSV with faculty,department,faculty_code,department_code
  # Then POST /api/academic/structure/bulk with file

  # Import Students_300 sheet via XLSX
  # Extract Students_300 sheet as XLSX and POST /api/academic/register/import

Example Python for Students import:

  import requests
  token = "<INST_TOKEN>"
  session_id = "<SESSION_ID from sessions call>"
  files = {"file": open("Students_300.xlsx","rb")}
  data = {"session_id": session_id, "dry_run": "true"}
  r = requests.post(f"{API_URL}/api/academic/register/import", headers={"Authorization": f"Bearer {token}"}, files=files, data=data)
  print(r.json())

  # Then dry_run false to actually import, file will be archived to Cloudinary if enabled

  # Import Staff via invitations bulk
  # Use Staff_Authorized sheet

  # Test workflows: acknowledge/route/respond/resolve
  # Measure processing time, routing accuracy, SLA compliance, errors, adoption, satisfaction
  # Capture de-identified screenshots showing dynamic escalation (PRIORITY_SLA_FACTOR)

  # After pilot, delete pilot data:
  # DELETE FROM complaints WHERE pilot_scenario_id IS NOT NULL or data_origin='pilot'
  # Then re-register FUW clean for production
""")

print(f"\nExcel file: {EXCEL_PATH}")
if EXCEL_PATH.exists():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    print(f"Sheets: {wb.sheetnames}")
else:
    print("Excel file not found, generate via python that created FUW_Pilot_Dataset_300_Students.xlsx")

print("\nDone. Check docs/FUW_PILOT_HARDENING.md for full hardening notes.")
