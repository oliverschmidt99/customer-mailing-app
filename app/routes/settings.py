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
    url_for,
)
from werkzeug.utils import secure_filename

bp = Blueprint("settings", __name__, url_prefix="/settings")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "svg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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

    # NEU: Logo-URL für das Template vorbereiten
    if config_data.get("logo_path") and os.path.exists(config_data["logo_path"]):
        # Erstelle eine relative URL, die vom Browser aus erreichbar ist
        logo_filename = os.path.basename(config_data["logo_path"])
        config_data["logo_url"] = url_for(
            "static", filename=f"user_data/{logo_filename}"
        )
    else:
        config_data["logo_url"] = None

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
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}

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


# NEU: Route für den Logo-Upload
@bp.route("/api/upload-logo", methods=["POST"])
def upload_logo():
    if "logo" not in request.files:
        return (
            jsonify({"success": False, "error": "Keine Datei im Request gefunden."}),
            400,
        )

    file = request.files["logo"]

    if file.filename == "":
        return jsonify({"success": False, "error": "Keine Datei ausgewählt."}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # Speicherort für User-Dateien (relativ zum static-Ordner)
        upload_dir = os.path.join(current_app.static_folder, "user_data")
        os.makedirs(upload_dir, exist_ok=True)

        # Absoluter Pfad zum Speichern der Datei
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)

        # Pfad in config.json speichern
        config_filepath = _get_config_filepath()
        try:
            with open(config_filepath, "r+", encoding="utf-8") as f:
                config_data = json.load(f)
                config_data["logo_path"] = save_path
                f.seek(0)
                json.dump(config_data, f, ensure_ascii=False, indent=2)
                f.truncate()
        except (FileNotFoundError, json.JSONDecodeError):
            with open(config_filepath, "w", encoding="utf-8") as f:
                json.dump({"logo_path": save_path}, f, ensure_ascii=False, indent=2)

        logo_url = url_for("static", filename=f"user_data/{filename}")
        return jsonify(
            {"success": True, "message": "Logo hochgeladen.", "logo_url": logo_url}
        )

    return jsonify({"success": False, "error": "Ungültiger Dateityp."}), 400
