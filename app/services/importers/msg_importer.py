# app/services/importers/msg_importer.py
"""This module handles the import of .msg files."""
import os
import re
import subprocess
import tempfile
import shutil
import sys
from typing import Dict, Any, List, Union
from ..gender_detector import get_anrede_from_vorname
from ..titel_detector import extract_titles


def _search_field(pattern: str, text: str) -> str:
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


def _parse_message_text(text: str) -> Dict[str, Any]:
    """
    Parst den reinen Text aus einer .msg-Datei, indem alle 'Feldname: Wert'-Paare
    im Kopfbereich der Datei automatisch extrahiert werden (generisches Parsen).
    """
    data = {}
    key_value_pairs = {}
    current_key = None

    # Status-Variablen für das Parsen von mehrzeiligen Werten (speziell Adresse)
    in_multi_line_field = False

    for line in text.splitlines():
        match = re.match(r"^(.+?):\s*(.*)", line)

        if match:
            # Ein neuer Key: Value-Paar beginnt
            key = match.group(1).strip()
            value = match.group(2).strip()

            # Wenn der aktuelle Key die Adresse war, beende den Adressblock
            if (
                current_key == "Business Address"
                and "Address" not in key
                and key != "Email Display As"
                and key != "Full Name"
            ):
                in_multi_line_field = False

            if key == "Business Address":
                # Starte einen mehrzeiligen Adressblock
                current_key = key
                # Fange den Rest der Zeile ab
                key_value_pairs[key] = value + "\n"
                in_multi_line_field = True
            else:
                current_key = key
                key_value_pairs[key] = value
                in_multi_line_field = False

        elif (
            in_multi_line_field
            and current_key == "Business Address"
            and line.strip()
            and not line.strip().startswith("-")
        ):
            # Setze den Wert in der nächsten Zeile fort (nur für die Adresse)
            key_value_pairs[current_key] += line.strip() + "\n"

    # 1. Adress-Parsing (strukturieren)
    business_address_raw = key_value_pairs.pop("Business Address", "").strip()

    if business_address_raw:
        address_parts = [
            p.strip() for p in business_address_raw.splitlines() if p.strip()
        ]

        if len(address_parts) > 0:
            street_line = address_parts[0]
            # KORREKTUR: Versuche, Straße und Hausnummer zu trennen
            street_match = re.match(r"^(.+?)\s+([\d\w\s/.-]+)$", street_line)
            if street_match:
                data["Straße"] = street_match.group(1).strip().rstrip(",")
                data["Hausnummer"] = street_match.group(2).strip()
            else:
                # Fallback, falls keine Hausnummer gefunden wird
                data["Straße"] = street_line

        if len(address_parts) > 1:
            # Suche nach Muster: PLZ Ort
            plz_ort_line = address_parts[1]
            plz_ort_match = re.match(r"(\d{4,5})\s+(.+)", plz_ort_line)
            if plz_ort_match:
                data["Postleitzahl"] = plz_ort_match.group(1).strip()
                data["Ort"] = plz_ort_match.group(2).strip()

    # 2. Finales Mapping/Bereinigen aller Key-Value-Paare
    for key, value in key_value_pairs.items():
        key = key.strip()

        # Ignoriere Metadaten/Trenner oder leere Werte
        if key.startswith("-") or not value:
            continue

        # Umbenennung für Konsistenz mit deutschen Vorlagen-Attributen
        if key == "Job Title":
            key = "Position"
        if key == "Company":
            key = "Firma"
        if key == "First Name":
            key = "Vorname"
        if key == "Last Name":
            key = "Nachname"
        if key == "Business":
            key = "Telefon (geschäftlich)"
        if key == "Home":
            key = "Telefon (privat)"
        if key == "Mobile":
            key = "Mobilnummer"
        if key == "Business Fax":
            key = "Faxnummer"
        if key == "Email":
            key = "E-Mail"

        # Ignoriere redundante/unbrauchbare Felder
        if key in ["Email Display As", "Full Name"]:
            continue

        # Füge alle anderen Felder hinzu. Adressfelder wurden durch 1. strukturiert.
        if key not in data:
            data[key] = value

    # 3. Anrede automatisch erkennen, falls nicht vorhanden
    if "Anrede" not in data and "Vorname" in data:
        anrede = get_anrede_from_vorname(data["Vorname"])
        if anrede:
            data["Anrede"] = anrede

    # 4. Titel aus Position extrahieren, falls nicht schon vorhanden
    if "Titel (akademisch)" not in data and "Position" in data:
        titel = extract_titles(data["Position"])
        if titel:
            data["Titel (akademisch)"] = ", ".join(titel)

    return {k: v for k, v in data.items() if v}


def parse_msg_file(file_path: str) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Extrahiert den Inhalt einer .msg-Datei, parst ihn und gibt die strukturierten Daten zurück.

    Verwendet temporäre Ordner für eine saubere Extraktion und umgeht Umgebungsprobleme
    durch die explizite Nutzung des aktuellen Python-Interpreters (sys.executable).
    """
    # Erstelle einen temporären Ordner (sauberer als ein Cache im Projektordner)
    temp_dir = tempfile.mkdtemp(prefix="msg_extract_")

    try:
        # Führe das extract_msg-Tool aus
        subprocess.run(
            [sys.executable, "-m", "extract_msg", "--out", temp_dir, file_path],
            capture_output=True,
            text=True,
            check=False,
            encoding="latin-1",
        )

        found_txt_path = None
        # Dateien, die interne Daten enthalten und ignoriert werden sollen
        ignored_files = ["attachments.txt", "rtf-body.txt", "body.html", "message.html"]

        # ROBUSDE SUCHE: Finde die erste brauchbare TXT-Datei im Temp-Ordner.
        for root, _, files in os.walk(temp_dir):
            for file in files:
                # Prüfe, ob es eine Textdatei ist und nicht auf der Ignorierliste steht
                if file.lower().endswith(".txt") and file.lower() not in ignored_files:
                    full_path = os.path.join(root, file)
                    found_txt_path = full_path
                    break
            if found_txt_path:
                break

        if not found_txt_path:
            # Zeile umgebrochen für bessere Lesbarkeit
            error_msg = (
                "Konnte keine extrahierte Textdatei (.txt) aus der MSG-Datei finden. "
                "Dies geschieht oft bei Kontakten, die nur Metadaten oder nicht "
                "unterstützte Formate enthalten."
            )
            return {"error": error_msg}

        # Verwende den gefundenen Pfad
        with open(found_txt_path, "r", encoding="utf-8", errors="ignore") as file:
            text = file.read()

        # Rückgabe muss eine Liste von Kontakten sein, um konsistent mit anderen Importern zu sein
        return [_parse_message_text(text)]

    finally:
        # Löscht den temporären Ordner IMMER, wenn die Funktion beendet ist (WICHTIG!)
        shutil.rmtree(temp_dir)
