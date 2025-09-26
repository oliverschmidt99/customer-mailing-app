# app/services/importers/msg_importer.py
import os
import re
import subprocess
import tempfile
import shutil


def _search_field(pattern, text):
    """
    Hilfsfunktion für die Regex-Suche. Verwendet re.DOTALL, um über Zeilenumbrüche
    zu suchen, und nimmt nur die erste Zeile des Treffers.
    """
    # re.DOTALL sorgt dafür, dass '.' auch Zeilenumbrüche matcht
    match = re.search(pattern, text, re.DOTALL)
    if match:
        value = match.group(1).strip()
        # Nimm nur die erste Zeile, falls der Regex zu viel erfasst hat.
        return value.split("\n")[0].strip()
    return ""


def _parse_message_text(text):
    """Parst den reinen Text aus einer .msg-Datei."""
    data = {}

    # Extrahiere die Felder mit Regex
    data["Vorname"] = _search_field(r"First Name:\s*(.*)", text)
    data["Nachname"] = _search_field(r"Last Name:\s*(.*)", text)
    data["Anrede"] = _search_field(r"Full Name:\s*(Herr|Frau)", text)
    data["Position"] = _search_field(r"Job Title:\s*(.*)", text)
    data["Firma"] = _search_field(r"Company:\s*(.*)", text)
    data["Telefon (geschäftlich)"] = _search_field(r"Business:\s*([+\d\s()/.-]+)", text)
    data["Telefon (privat)"] = _search_field(r"Home:\s*([+\d\s()/.-]+)", text)
    data["Mobilnummer"] = _search_field(r"Mobile:\s*([+\d\s()/.-]+)", text)
    data["Faxnummer"] = _search_field(r"Fax:\s*([+\d\s()/.-]+)", text)
    data["E-Mail"] = _search_field(r"Email:\s*([\w\.-]+@[\w\.-]+)", text)

    # Adress-Parsing
    business_address = _search_field(r"Business Address:\s*(.*)", text)
    if business_address:
        addr_match = re.match(r"(.+),\s*(\d{4,5})\s+(.+)", business_address)
        if addr_match:
            data["Straße"] = addr_match.group(1).strip()
            data["Postleitzahl"] = addr_match.group(2).strip()
            data["Ort"] = addr_match.group(3).strip()
        else:
            data["Straße"] = business_address

    return {k: v for k, v in data.items() if v}  # Nur gefüllte Felder zurückgeben


def parse_msg_file(file_path):
    """
    Extrahiert den Inhalt einer .msg-Datei, parst ihn und gibt die strukturierten Daten zurück.
    """
    # Das ist der TEMP-Ordner im Flask-Kontext
    temp_dir = tempfile.mkdtemp(prefix="msg_extract_")

    try:
        # Führe das extract_msg-Tool aus
        subprocess.run(
            ["python", "-m", "extract_msg", "--out", temp_dir, file_path],
            capture_output=True,
            text=True,
            check=False,
        )

        found_txt_path = None
        # Dateien, die interne Daten enthalten und ignoriert werden sollen
        ignored_files = ["attachments.txt", "rtf-body.txt", "body.html", "message.html"]

        # FIX: Verwende os.walk, um in allen Unterordnern zu suchen (wie im erfolgreichen Test!)
        for root, _, files in os.walk(temp_dir):
            for file in files:
                # Prüfe, ob es eine Textdatei ist und nicht auf der Ignorierliste steht
                if file.lower().endswith(".txt") and file.lower() not in ignored_files:
                    full_path = os.path.join(root, file)
                    found_txt_path = full_path
                    break  # Wir nehmen die erste gefundene (message.txt oder Kontaktname.txt)
            if found_txt_path:
                break

        if not found_txt_path:
            return {
                "error": "Konnte keine extrahierte Textdatei (.txt) aus der MSG-Datei finden. Dies geschieht oft bei Kontakten, die nur Metadaten oder nicht unterstützte Formate enthalten."
            }

        # Verwende den gefundenen Pfad
        with open(found_txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        return [_parse_message_text(text)]

    finally:
        # Löscht den temporären Ordner IMMER, wenn die Funktion beendet ist (das ist wichtig für die Sicherheit)
        shutil.rmtree(temp_dir)
