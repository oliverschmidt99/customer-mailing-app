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


def _get_config_filepath():
    """Gibt den Pfad zur allgemeinen Konfigurationsdatei zurück."""
    return os.path.join(current_app.root_path, "..", "data", "config.json")


@bp.route("/")
def index():
    """Zeigt die Einstellungsseite an."""
    options_filepath = _get_options_filepath()
    config_filepath = _get_config_filepath()

    options_data = {"options": []}
    config_data = {}

    try:
        with open(options_filepath, "r", encoding="utf-8") as f:
            options_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        flash("Warnung: Konnte die 'selection_options.json' nicht laden.", "warning")

    try:
        with open(config_filepath, "r", encoding="utf-8") as f:
            config_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        flash("Warnung: Konnte die 'config.json' nicht laden.", "warning")

    return render_template(
        "settings.html",
        selection_options=options_data.get("options", []),
        config=config_data,
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


@bp.route("/api/config", methods=["POST"])
def save_config():
    """Speichert die allgemeine Konfiguration."""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Ungültige Daten."}), 400

    filepath = _get_config_filepath()
    try:
        # Lese bestehende Konfiguration, um andere Werte nicht zu überschreiben
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}

        # Aktualisiere nur die übergebenen Schlüssel
        config_data.update(data)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "message": "Einstellungen gespeichert."})
    except IOError as e:
        return (
            jsonify(
                {"success": False, "error": f"Fehler beim Speichern der Datei: {e}"}
            ),
            500,
        )
