# app/routes/main.py
"""This module defines the main routes for the application, like the homepage."""
from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Zeigt die Startseite an."""
    return render_template("index.html")


# Die alte `/settings`-Route wurde von hier entfernt.
# Die korrekte Logik befindet sich jetzt in `app/routes/settings.py`.
