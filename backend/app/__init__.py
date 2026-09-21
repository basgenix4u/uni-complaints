"""Application factory."""

from flask import Flask, jsonify, request

from app.config import get_config
from app.extensions import bcrypt, cors, db, jwt, limiter, migrate
from app.observability import configure_logging, configure_sentry, register_request_logging


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    # A regex is added only when configured, so the default stays an
    # explicit allowlist.
    cors_resource = {"origins": app.config["CORS_ORIGINS"]}
    if app.config.get("CORS_ORIGIN_REGEX"):
        cors_resource["origins"] = (
            app.config["CORS_ORIGINS"] + [app.config["CORS_ORIGIN_REGEX"]]
        )
    cors.init_app(
        app,
        resources={r"/api/*": cors_resource},
        supports_credentials=True,
        expose_headers=["X-Request-ID"],
    )

    from app import models  # noqa: F401  (registers tables with Flask-Migrate)
    from app.routes.admin import bp as admin_bp
    from app.routes.attachments import bp as attachments_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.complaints import bp as complaints_bp, public_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.notifications import bp as notifications_bp
    from app.routes.platform import bp as platform_bp
    from app.routes.invitations import bp as invitations_bp, public_bp as invitation_public_bp
    from app.routes.privacy import bp as privacy_bp
    from app.routes.routing import bp as routing_bp, platform_bp as routing_platform_bp
    from app.routes.tasks import bp as tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(platform_bp)
    app.register_blueprint(invitations_bp)
    app.register_blueprint(invitation_public_bp)
    app.register_blueprint(privacy_bp)
    app.register_blueprint(routing_bp)
    app.register_blueprint(routing_platform_bp)
    app.register_blueprint(tasks_bp)

    logger = configure_logging(app)
    configure_sentry(app)
    register_request_logging(app, logger)

    register_error_handlers(app, logger)
    register_jwt_handlers(app)
    register_cli(app)

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "status": "ok"})

    @app.get("/api/ready")
    def ready():
        """Readiness probe: confirms the database answers."""
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"success": True, "status": "ready"})
        except Exception:
            return jsonify({"success": False, "status": "database unavailable"}), 503

    @app.after_request
    def security_headers(response):
        # The API returns JSON only, so a restrictive policy costs nothing
        # and closes off sniffing and framing.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if not app.debug:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        # Attachments and personal data must not be cached by proxies.
        if request.path.startswith("/api/") and request.path != "/api/health":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app


def register_error_handlers(app: Flask, logger=None) -> None:
    """Return JSON for every error so the client never has to parse HTML.

    Every response carries the request id, so somebody reporting a problem
    can quote a value that finds the exact request in the logs.
    """
    from app.observability import request_id

    def problem(message: str, status: int):
        body = {"success": False, "message": message}
        reference = request_id()
        if reference:
            body["reference"] = reference
        return jsonify(body), status

    @app.errorhandler(400)
    def bad_request(_):
        return problem("We could not read that request.", 400)

    @app.errorhandler(404)
    def not_found(_):
        return problem("We could not find that.", 404)

    @app.errorhandler(413)
    def too_large(_):
        return problem("That file is too large.", 413)

    @app.errorhandler(429)
    def rate_limited(_):
        return problem("Too many attempts. Please wait a moment.", 429)

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        if logger:
            # The detail goes to the log; the caller gets a reference.
            logger.exception("unhandled_error", error=str(error))
        return problem(
            "Something went wrong on our side. Quote the reference below if you contact support.",
            500,
        )


def register_jwt_handlers(app: Flask) -> None:
    @jwt.expired_token_loader
    def expired(_h, _p):
        return jsonify({"success": False, "message": "Your session has expired. Please sign in again."}), 401

    @jwt.invalid_token_loader
    def invalid(_r):
        return jsonify({"success": False, "message": "Your session is not valid. Please sign in again."}), 401

    @jwt.unauthorized_loader
    def missing(_r):
        return jsonify({"success": False, "message": "Please sign in to continue."}), 401


def register_cli(app: Flask) -> None:
    import click

    @app.cli.command("send-queue")
    def send_queue():
        """Deliver queued email and text messages."""
        from app.services.delivery import process_queue

        result = process_queue()
        click.echo(f"Sent {result['sent']}, failed {result['failed']}.")

    @app.cli.command("purge-expired")
    def purge_expired():
        """Apply each institution's retention period.

        Storage limitation means personal data is not kept indefinitely.
        Intended to run nightly.
        """
        from app.models.institution import Institution
        from app.services.privacy import purge_expired_data

        total = 0
        for institution in Institution.query.filter(Institution.retention_months > 0).all():
            result = purge_expired_data(institution)
            purged = result.get("complaints_purged", 0)
            total += purged
            if purged:
                click.echo(f"{institution.code}: purged {purged}")
        click.echo(f"Purged {total} expired complaints.")

    @app.cli.command("escalate")
    def escalate():
        """Escalate complaints past their deadline.

        Intended to run on a schedule, for example every 30 minutes.
        """
        from app.services.sla import run_escalation_sweep

        result = run_escalation_sweep()
        click.echo(
            f"Escalated {result['escalated']}, reminded {result['reminded']}."
        )

    @app.cli.command("report-ignored")
    @click.option("--force", is_flag=True, help="Send now, ignoring the weekly interval.")
    def report_ignored(force):
        """Email each institution's head what it has left unanswered.

        The interval is enforced inside the service rather than by the
        schedule, so running this more often does not produce a weekly
        report more often.
        """
        from app.services.routing import report_ignored_everywhere

        result = report_ignored_everywhere(force=force)
        click.echo(
            f"Reported {result['complaints_ignored']} ignored complaint(s) at "
            f"{result['institutions_reported']} institution(s)."
        )

    @app.cli.command("seed")
    @click.option("--demo", is_flag=True, help="Also create a demo institution and accounts.")
    def seed(demo):
        """Create the platform administrator, and optionally demo data.

        Resolves the bootstrap problem: staff accounts are created by an
        administrator, so the first one has to come from outside the API.
        """
        import os

        from app.models.institution import Institution
        from app.models.user import User

        db.create_all()

        email = os.getenv("PLATFORM_ADMIN_EMAIL", "admin@resolve.ng").lower()
        password = os.getenv("PLATFORM_ADMIN_PASSWORD", "ChangeMe123")

        if not User.query.filter_by(email=email, role="platform_admin").first():
            admin = User(full_name="Platform Administrator", email=email, role="platform_admin")
            admin.set_password(password)
            db.session.add(admin)
            click.echo(f"Created platform administrator: {email}")

        if demo:
            institution = Institution.query.filter_by(slug="demo-university").first()
            if not institution:
                institution = Institution(
                    name="Demo University",
                    code="DMU",
                    slug="demo-university",
                    state="FCT",
                    contact_email="support@demo.edu.ng",
                )
                db.session.add(institution)
                db.session.flush()

                # The standard units and a working routing table, so the
                # demo behaves like a real institution rather than
                # dropping every complaint into one unassigned pile.
                from app.services.routing import seed_routing, seed_units

                seed_units(institution)
                db.session.flush()
                seed_routing(institution)
                db.session.flush()

                staff = User(
                    institution_id=institution.id,
                    full_name="Institution Admin",
                    email="admin@demo.edu.ng",
                    role="institution_admin",
                )
                staff.set_password("Password123")
                db.session.add(staff)

                student = User(
                    institution_id=institution.id,
                    full_name="Amina Yusuf",
                    email="amina@demo.edu.ng",
                    matric_number="ENG/COE/21/013",
                    faculty="Engineering",
                    role="student",
                )
                student.set_password("Password123")
                db.session.add(student)
                click.echo("Created demo institution, staff and student accounts.")

        db.session.commit()
        click.echo("Seed complete.")
