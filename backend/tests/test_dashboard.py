from tests.conftest import auth, login, make_user

COMPLAINT = {
    "title": "Missing result for CSC 301",
    "description": "My result has not appeared on the portal since the semester ended.",
    "category": "result_issues",
    "priority": "medium",
}


def file_complaint(client, token, **overrides):
    return client.post("/api/complaints", headers=auth(token), json={**COMPLAINT, **overrides})


def test_students_cannot_reach_the_admin_dashboard(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    for path in ("/api/dashboard/overview", "/api/dashboard/charts/status"):
        assert client.get(path, headers=auth(token)).status_code == 403


def test_overview_counts_only_the_callers_institution(client, alpha, beta):
    make_user(alpha, "alpha.student@test.ng")
    make_user(alpha, "alpha.officer@test.ng", role="officer")
    make_user(beta, "beta.student@test.ng")

    alpha_student = login(client, "alpha.student@test.ng")
    file_complaint(client, alpha_student)
    file_complaint(client, alpha_student, title="Second complaint here")

    beta_student = login(client, "beta.student@test.ng")
    file_complaint(client, beta_student, title="Beta complaint entirely")

    officer = login(client, "alpha.officer@test.ng")
    overview = client.get("/api/dashboard/overview", headers=auth(officer)).get_json()["data"]

    assert overview["overview"]["total_complaints"] == 2
    assert overview["today"]["new"] == 2


def test_trend_chart_fills_days_with_no_activity(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    response = client.get("/api/dashboard/charts/trend?days=7", headers=auth(token))

    assert response.status_code == 200
    assert len(response.get_json()["data"]["chart_data"]) == 7


def test_monthly_chart_always_returns_twelve_months(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    data = client.get("/api/dashboard/charts/monthly", headers=auth(token)).get_json()["data"]

    assert len(data["chart_data"]) == 12
    assert data["chart_data"][0]["month_name"] == "Jan"


def test_student_stats_cover_only_their_own_complaints(client, alpha):
    make_user(alpha, "one@test.ng")
    make_user(alpha, "two@test.ng")

    first = login(client, "one@test.ng")
    file_complaint(client, first)
    file_complaint(client, first, title="Another complaint filed")

    second = login(client, "two@test.ng")
    file_complaint(client, second, title="Different student complaint")

    stats = client.get("/api/dashboard/student-stats", headers=auth(second)).get_json()["data"]

    assert stats["statistics"]["total"] == 1
    assert stats["statistics"]["pending"] == 1


def test_average_resolution_time_is_reported(client, alpha):
    make_user(alpha, "student@test.ng")
    make_user(alpha, "officer@test.ng", role="officer")

    student = login(client, "student@test.ng")
    complaint_id = file_complaint(client, student).get_json()["data"]["complaint"]["id"]

    officer = login(client, "officer@test.ng")
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "in_progress"})
    client.put(f"/api/complaints/{complaint_id}/status", headers=auth(officer),
               json={"status": "resolved", "note": "Result has now been uploaded."})

    overview = client.get("/api/dashboard/overview", headers=auth(officer)).get_json()["data"]

    assert overview["overview"]["avg_resolution_time_hours"] >= 0
    assert overview["overview"]["resolution_rate"] == 100.0


def test_staff_performance_requires_department_head(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    make_user(alpha, "head@test.ng", role="dept_head")

    officer = login(client, "officer@test.ng")
    assert client.get("/api/dashboard/reports/staff-performance",
                      headers=auth(officer)).status_code == 403

    head = login(client, "head@test.ng")
    assert client.get("/api/dashboard/reports/staff-performance",
                      headers=auth(head)).status_code == 200


def test_the_monthly_chart_counts_complaints_in_the_right_month(client, alpha, db):
    """The shape test above passes on a chart that counts nothing.

    This endpoint used strftime, which is SQLite only and raises
    UndefinedFunction on PostgreSQL, so it returned a 500 on every real
    deployment while its test stayed green.
    """
    from datetime import datetime, timezone

    from app.models.complaint import Complaint

    student = make_user(alpha, "student@test.ng")
    for month, count in ((3, 2), (7, 1)):
        for index in range(count):
            db.session.add(
                Complaint(
                    institution_id=alpha.id,
                    student_id=student.id,
                    ticket_number=f"AAA-M{month:02d}-{index:04d}",
                    title="Fees receipt not reflecting",
                    description="I paid three weeks ago and the portal still shows unpaid.",
                    category="fees_payment",
                    status="submitted",
                    created_at=datetime(2026, month, 15, 12, 0, tzinfo=timezone.utc),
                )
            )
    db.session.commit()

    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    data = client.get(
        "/api/dashboard/charts/monthly?year=2026", headers=auth(token)
    ).get_json()["data"]

    by_month = {row["month"]: row["count"] for row in data["chart_data"]}
    assert by_month[3] == 2
    assert by_month[7] == 1
    assert by_month[1] == 0


def test_the_monthly_chart_excludes_other_years(client, alpha, db):
    from datetime import datetime, timezone

    from app.models.complaint import Complaint

    student = make_user(alpha, "student@test.ng")
    db.session.add(
        Complaint(
            institution_id=alpha.id,
            student_id=student.id,
            ticket_number="AAA-YEAR-0001",
            title="Filed the previous year",
            description="This belongs to the year before and must not be counted.",
            category="fees_payment",
            status="submitted",
            created_at=datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc),
        )
    )
    db.session.commit()

    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    data = client.get(
        "/api/dashboard/charts/monthly?year=2026", headers=auth(token)
    ).get_json()["data"]

    assert sum(row["count"] for row in data["chart_data"]) == 0


def test_an_absurd_year_is_refused(client, alpha):
    make_user(alpha, "officer@test.ng", role="officer")
    token = login(client, "officer@test.ng")

    response = client.get("/api/dashboard/charts/monthly?year=99999", headers=auth(token))

    assert response.status_code == 422
