# app/routes/settings.py
"""This module defines the routes for the settings page."""
import json
import os
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    current_app,
    flash,
)

bp = Blueprint("settings", __name__, url_prefix="/settings")


def _get_options_filepath():
    """Gibt den Pfad zur JSON-Datei mit den Auswahloptionen zurück."""
    return os.path.join(current_app.root_path, "..", "data", "selection_options.json")


@bp.route("/")
def index():
    """Zeigt die Einstellungsseite an."""
    filepath = _get_options_filepath()
    options_data = {"options": []}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            options_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        flash("Warnung: Konnte die 'selection_options.json' nicht laden.", "warning")

    return render_template(
        "settings.html", selection_options=options_data.get("options", [])
    )


@bp.route("/api/selection-options", methods=["POST"])
def save_selection_options():
    """Speichert die geänderten Auswahloptionen in der JSON-Datei."""
    data = request.get_json()
    if not isinstance(data, dict) or "options" not in data:
        return jsonify({"success": False, "error": "Ungültige Daten."}), 400

    filepath = _get_options_filepath()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "message": "Auswahloptionen gespeichert."})
    except IOError as e:
        return (
            jsonify(
                {"success": False, "error": f"Fehler beim Speichern der Datei: {e}"}
            ),
            500,
        )
