# app/routes/import_export.py
"""This module handles the import and export of contact data."""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple

from flask import Blueprint, request, jsonify, flash, url_for, Response, current_app
from flask_executor import Executor
from werkzeug.utils import secure_filename

from ..models import db, Vorlage, Kontakt
from ..services import importer_service, exporter_service

bp = Blueprint("import_export", __name__)
ALLOWED_EXTENSIONS = {"csv", "msg", "oft", "txt", "vcf", "xlsx"}

# Ein einfacher In-Memory-Speicher für den Fortschritt der Tasks
task_progress = {}


def process_files_task(task_id: str, file_paths: List[Dict[str, str]]):
    """
    Diese Funktion läuft im Hintergrund und verarbeitet die hochgeladenen Dateien.
    """
    total_files = len(file_paths)
    all_records: List[Dict[str, Any]] = []
    error_list: List[Dict[str, str]] = []

    task_progress[task_id] = {
        "status": "processing",
        "progress": 0,
        "total": total_files,
        "result": None,
    }

    for i, file_info in enumerate(file_paths):
        filename = file_info["original_name"]
        filepath = file_info["path"]

        try:
            data = importer_service.import_file_from_path(filepath)
            if isinstance(data, dict) and "error" in data:
                error_list.append({"filename": filename, "error": data["error"]})
            else:
                all_records.extend(data)
        except (IOError, ValueError) as e:
            error_list.append(
                {"filename": filename, "error": f"Systemfehler: {str(e)}"}
            )
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

        task_progress[task_id]["progress"] = i + 1

    all_headers = set(key for record in all_records for key in record.keys())

    task_progress[task_id]["status"] = "complete"
    task_progress[task_id]["result"] = {
        "headers": list(all_headers),
        "preview_data": all_records[:5],
        "original_data": all_records,
        "errors": error_list,
    }


@bp.route("/import/upload", methods=["POST"])
def upload_import_file():
    """
    Nimmt Dateien entgegen, startet die Hintergrundverarbeitung und gibt eine Task-ID zurück.
    """
    if "files" not in request.files:
        return jsonify({"error": "Keine Dateien im Request gefunden."}), 400

    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        return jsonify({"error": "Keine Dateien ausgewählt."}), 400

    executor = Executor(current_app)
    task_id = uuid.uuid4().hex
    temp_dir = current_app.config["UPLOAD_FOLDER"]
    file_paths = []

    for file in files:
        filename = secure_filename(file.filename) if file.filename else "tempfile"
        file_ext = os.path.splitext(filename)[1].lower()

        temp_filename = f"{task_id}_{uuid.uuid4().hex}{file_ext}"
        filepath = os.path.join(temp_dir, temp_filename)
        file.save(filepath)
        file_paths.append({"path": filepath, "original_name": file.filename})

    executor.submit(process_files_task, task_id, file_paths)

    return jsonify({"task_id": task_id}), 202


@bp.route("/import/status/<string:task_id>", methods=["GET"])
def get_import_status(task_id: str):
    """
    Gibt den aktuellen Status einer Hintergrundaufgabe zurück.
    """
    progress = task_progress.get(task_id)
    if not progress:
        return jsonify({"error": "Task nicht gefunden"}), 404

    if progress["status"] == "complete":
        result_data = progress["result"]
        task_progress.pop(task_id, None)  # Sicher entfernen
        return jsonify({"status": "complete", "data": result_data})

    return jsonify(progress)


@bp.route("/import/finalize", methods=["POST"])
def finalize_import():
    """
    Speichert die importierten und zugeordneten Kontaktdaten in der Datenbank.
    """
    data = request.get_json()
    vorlage_id = data.get("vorlage_id")
    mappings = data.get("mappings")
    original_data = data.get("original_data")

    if not all([vorlage_id, mappings, original_data]):
        return jsonify({"success": False, "error": "Fehlende Daten."}), 400

    vorlage = db.session.get(Vorlage, vorlage_id)
    if not vorlage:
        return jsonify({"success": False, "error": "Vorlage nicht gefunden."}), 404

    count = 0
    for row in original_data:
        new_kontakt_data = {
            vorlage_prop: row.get(import_header)
            for import_header, vorlage_prop in mappings.items()
            if vorlage_prop
        }
        if new_kontakt_data:
            kontakt = Kontakt(vorlage_id=vorlage_id)
            kontakt.set_data(new_kontakt_data)
            db.session.add(kontakt)
            count += 1

    db.session.commit()
    flash(f"{count} Kontakte wurden erfolgreich importiert.", "success")
    return jsonify({"success": True, "redirect_url": url_for("kontakte.auflisten")})


@bp.route("/export/<int:vorlage_id>/<string:file_format>")
def export_data(vorlage_id: int, file_format: str) -> Tuple[Response, int] | Response:
    """
    Exportiert die Kontaktdaten einer Vorlage im angegebenen Format.
    """
    vorlage_model = db.session.get(Vorlage, vorlage_id)
    if not vorlage_model:
        return "Vorlage nicht gefunden", 404

    kontakte_data = [
        {"id": k.id, "daten": k.get_data()} for k in vorlage_model.kontakte
    ]
    vorlage_struktur = {
        "name": vorlage_model.name,
        "gruppen": [
            {
                "name": g.name,
                "eigenschaften": [{"name": e.name} for e in g.eigenschaften],
            }
            for g in vorlage_model.gruppen
        ],
    }

    content, mimetype = exporter_service.export_data(
        file_format, kontakte_data, vorlage_struktur
    )

    if not content:
        return "Ungültiges Export-Format", 400

    filename = f"{vorlage_model.name}_export_{datetime.now().strftime('%Y-%m-%d')}.{file_format}"

    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )
