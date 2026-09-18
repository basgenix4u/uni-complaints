"""Application factory."""

from flask import Flask, jsonify

from app.config import get_config
from app.extensions import bcrypt, cors, db, jwt, limiter, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    from app import models  # noqa: F401  (registers tables with Flask-Migrate)
    from app.routes.admin import bp as admin_bp
    from app.routes.attachments import bp as attachments_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.complaints import bp as complaints_bp, public_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.notifications import bp as notifications_bp
    from app.routes.platform import bp as platform_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attachments_bp)
    app.register_blueprint(platform_bp)

    register_error_handlers(app)
    register_jwt_handlers(app)
    register_cli(app)

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "status": "ok"})

    return app


def register_error_handlers(app: Flask) -> None:
    """Return JSON for every error so the client never has to parse HTML."""

    @app.errorhandler(400)
    def bad_request(_):
        return jsonify({"success": False, "message": "We could not read that request."}), 400

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"success": False, "message": "We could not find that."}), 404

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"success": False, "message": "That file is too large."}), 413

    @app.errorhandler(429)
    def rate_limited(_):
        return jsonify({"success": False, "message": "Too many attempts. Please wait a moment."}), 429

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return jsonify({"success": False, "message": "Something went wrong on our side."}), 500


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

    @app.cli.command("seed")
    @click.option("--demo", is_flag=True, help="Also create a demo institution and accounts.")
    def seed(demo):
        """Create the platform administrator, and optionally demo data.

        Resolves the bootstrap problem: staff accounts are created by an
        administrator, so the first one has to come from outside the API.
        """
        import os

        from app.models.institution import Department, Institution
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

                for name, slug in (
                    ("Bursary", "bursary"),
                    ("Registry", "registry"),
                    ("Student Affairs", "student-affairs"),
                ):
                    db.session.add(
                        Department(institution_id=institution.id, name=name, slug=slug)
                    )
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
