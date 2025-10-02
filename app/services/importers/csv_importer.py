# app/services/importers/csv_importer.py
import csv
from ..gender_detector import get_anrede_from_vorname
from ..titel_detector import extract_titles


def parse_csv_txt(file_path, delimiter=","):
    """
    Liest CSV- oder TXT-Dateien, gibt eine Liste von Dictionaries und den rohen Inhalt zurück.
    """
    records = []
    raw_content = ""
    try:
        with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
            f.seek(0)  # Zurück zum Anfang der Datei für das Parsen
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Automatische Erkennung von Anrede und Titel
                if not row.get("Anrede"):
                    if row.get("Vorname"):
                        anrede = get_anrede_from_vorname(row["Vorname"])
                        if anrede:
                            row["Anrede"] = anrede
                if not row.get("Titel (akademisch)"):
                    if row.get("Position"):
                        titel = extract_titles(row["Position"])
                        if titel:
                            row["Titel (akademisch)"] = ", ".join(titel)
                records.append(row)
    except Exception:
        # Fallback für andere Kodierungen
        with open(file_path, mode="r", encoding="latin-1", errors="ignore") as f:
            raw_content = f.read()
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                # Dieselbe Logik hier für den Fallback
                if not row.get("Anrede"):
                    if row.get("Vorname"):
                        anrede = get_anrede_from_vorname(row["Vorname"])
                        if anrede:
                            row["Anrede"] = anrede
                if not row.get("Titel (akademisch)"):
                    if row.get("Position"):
                        titel = extract_titles(row["Position"])
                        if titel:
                            row["Titel (akademisch)"] = ", ".join(titel)
                records.append(row)

    return records, raw_content
