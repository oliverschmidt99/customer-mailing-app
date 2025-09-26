# app/routes/import_export.py
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

from flask import Blueprint, request, jsonify, flash, url_for, Response
from ..models import db, Vorlage, Kontakt
from ..services import importer_service, exporter_service

bp = Blueprint("import_export", __name__)
ALLOWED_EXTENSIONS = {"csv", "msg", "oft", "txt", "vcf", "xlsx"}


@bp.route("/import/upload", methods=["POST"])
def upload_import_file():
    """
    Verarbeitet den Upload einer oder mehrerer Dateien, extrahiert die Kontaktdaten
    und gibt die Ergebnisse zur Zuordnung zurück. Fehlerhafte Dateien werden
    ignoriert und protokolliert.
    """
    if "files" not in request.files:
        return jsonify({"error": "Keine Dateien im Request gefunden."}), 400

    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        return jsonify({"error": "Keine Dateien ausgewählt."}), 400

    all_records: List[Dict[str, Any]] = []
    error_list: List[Dict[str, str]] = []

    for file in files:
        filename = file.filename if file.filename else "Unbekannt"
        file_ext = os.path.splitext(filename)[1].lower().replace(".", "")

        if file_ext not in ALLOWED_EXTENSIONS:
            error_list.append(
                {"filename": filename, "error": f"Dateityp '{file_ext}' nicht erlaubt."}
            )
            continue

        try:
            # Wichtig: Dateiobjekt zurück zum Anfang setzen
            file.seek(0)
            data = importer_service.import_file(file)

            if isinstance(data, dict) and "error" in data:
                # Fehler vom Importer-Service (z.B. von msg_importer)
                error_list.append({"filename": filename, "error": data["error"]})
            else:
                # Erfolg: Daten zur Liste hinzufügen
                all_records.extend(data)

        except (IOError, OSError, ValueError) as e:
            # Spezifische Fehler beim Datei-Handling oder Parsen
            error_list.append(
                {"filename": filename, "error": f"Fehler beim Lesen/Parsen: {str(e)}"}
            )
        except Exception as e:
            # Fängt alle unerwarteten restlichen Fehler ab
            error_list.append(
                {
                    "filename": filename,
                    "error": f"Unerwarteter Systemfehler: {type(e).__name__} - {str(e)}",
                }
            )

    if not all_records and error_list:
        # Alle Dateien waren fehlerhaft
        return (
            jsonify(
                {
                    "error": "Es konnten keine gültigen Daten importiert werden.",
                    "errors": error_list,
                }
            ),
            400,
        )

    if not all_records:
        return jsonify({"error": "Keine Daten in den Dateien gefunden."}), 400

    # Sammle alle eindeutigen Spaltennamen aus allen erfolgreichen Records
    all_headers = set()
    for record in all_records:
        all_headers.update(record.keys())

    preview_data = all_records[:5]

    # Gebe die erfolgreichen Daten und die Fehlerliste zurück
    return jsonify(
        {
            "headers": list(all_headers),
            "preview_data": preview_data,
            "original_data": all_records,
            "errors": error_list,
        }
    )


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
        return (
            jsonify({"success": False, "error": "Fehlende Daten für den Import."}),
            400,
        )

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
