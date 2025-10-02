# app/services/importer_service.py
"""This service handles the file import logic."""
import os
from typing import Dict, Any, List, Union, Tuple

from flask import current_app
from .importers import csv_importer, msg_importer, vcf_importer, xlsx_importer


def import_file_from_path(
    file_path: str,
) -> Union[Tuple[List[Dict[str, Any]], str], Dict[str, str]]:
    """
    Erkennt den Dateityp eines existierenden Pfades und ruft den entsprechenden Parser auf.
    Gibt die geparsten Daten und den rohen Inhalt zurück.

    Args:
        file_path: Der vollständige Pfad zur zu importierenden Datei.

    Returns:
        Ein Tupel (Liste von Kontakten, Rohdaten-String) oder ein Fehler-Dictionary.
    """
    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()

    try:
        if file_ext == ".csv":
            return csv_importer.parse_csv_txt(file_path, delimiter=",")
        if file_ext == ".txt":
            return csv_importer.parse_csv_txt(file_path, delimiter="\t")
        if file_ext == ".xlsx":
            return xlsx_importer.parse_xlsx(file_path)
        if file_ext == ".vcf":
            return vcf_importer.parse_vcf(file_path)
        if file_ext in [".msg", ".oft"]:
            return msg_importer.parse_msg_file(file_path)

        return {"error": f"Dateityp {file_ext} wird nicht unterstützt."}
    except (IOError, ValueError) as e:
        # Fange spezifische Parser-Fehler ab
        current_app.logger.error(f"Parser-Fehler bei Datei {filename}: {e}")
        return {"error": "Fehler beim Parsen der Datei."}
