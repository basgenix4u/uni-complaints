"""Development entry point."""

import os

from app import create_app
from app.extensions import db

app = create_app()


@app.shell_context_processor
def shell_context():
    from app.models import Complaint, Department, Institution, Notification, Response, User

    return {
        "db": db,
        "Institution": Institution,
        "Department": Department,
        "User": User,
        "Complaint": Complaint,
        "Response": Response,
        "Notification": Notification,
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "True").lower() == "true",
    )
