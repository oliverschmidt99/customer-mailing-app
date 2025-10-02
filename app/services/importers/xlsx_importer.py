# app/services/importers/xlsx_importer.py
import openpyxl
from ..gender_detector import get_anrede_from_vorname
from ..titel_detector import extract_titles


def parse_xlsx(file_path):
    """
    Liest eine .xlsx-Datei, gibt eine Liste von Dictionaries und eine Text-Repräsentation zurück.
    """
    records = []
    raw_content_lines = []
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active

    # Konvertiere Header zu Strings, um Fehler bei leeren oder Nicht-String-Zellen zu vermeiden
    headers = [str(cell.value) if cell.value is not None else "" for cell in sheet[1]]
    raw_content_lines.append("\t".join(headers))

    for row_values in sheet.iter_rows(min_row=2, values_only=True):
        if any(cell is not None for cell in row_values):
            row_dict = dict(zip(headers, row_values))

            # Automatische Erkennung von Anrede und Titel
            if not row_dict.get("Anrede"):
                if row_dict.get("Vorname"):
                    anrede = get_anrede_from_vorname(str(row_dict["Vorname"]))
                    if anrede:
                        row_dict["Anrede"] = anrede
            if not row_dict.get("Titel (akademisch)"):
                if row_dict.get("Position"):
                    titel = extract_titles(str(row_dict["Position"]))
                    if titel:
                        row_dict["Titel (akademisch)"] = ", ".join(titel)

            records.append(row_dict)
            # Konvertiere alle Werte der Zeile für den rohen Inhalt in Strings
            raw_content_lines.append(
                "\t".join(str(v) if v is not None else "" for v in row_values)
            )

    raw_content = "\n".join(raw_content_lines)
    return records, raw_content
