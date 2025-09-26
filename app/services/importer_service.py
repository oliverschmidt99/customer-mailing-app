# app/services/importer_service.py
"""This service handles the file import logic."""
import os
from typing import Dict, Any, List, Union

from flask import current_app
from werkzeug.utils import secure_filename

# KORRIGIERTER IMPORT-PFAD: Nutzt relative Imports innerhalb des 'app'-Pakets
from .importers import csv_importer, msg_importer, vcf_importer, xlsx_importer


def import_file(file_storage) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Erkennt den Dateityp und ruft den entsprechenden Parser auf.

    Args:
        file_storage: Das FileStorage-Objekt von Flask.

    Returns:
        Eine Liste von Kontaktdaten-Dictionaries oder ein Fehler-Dictionary.
    """
    filename = secure_filename(file_storage.filename)
    file_ext = os.path.splitext(filename)[1].lower()

    temp_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, filename)
    file_storage.save(file_path)

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

        return {
            "error": f"Dateityp {file_ext} wird für den Import noch nicht unterstützt."
        }
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
