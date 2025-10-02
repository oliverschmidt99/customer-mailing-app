# app/services/gender_detector.py
"""This module provides a service to guess the gender based on a first name."""
import gender_guesser.detector as gender


def get_anrede_from_vorname(vorname: str) -> str:
    """
    Ermittelt die Anrede ('Herr'/'Frau') anhand eines Vornamens.
    Gibt einen leeren String zurück, wenn der Name nicht eindeutig ist.
    """
    if not vorname or not isinstance(vorname, str):
        return ""

    # Initialisiere den Detektor (unabhängig von Groß-/Kleinschreibung)
    detector = gender.Detector(case_sensitive=False)

    # get_gender gibt 'male', 'female', 'mostly_male', 'mostly_female',
    # 'andy' oder 'unknown' zurück.
    geschlecht = detector.get_gender(
        vorname.split()[0]
    )  # Nur den ersten Vornamen prüfen

    if geschlecht in ("male", "mostly_male"):
        return "Herr"
    if geschlecht in ("female", "mostly_female"):
        return "Frau"

    # Für 'andy' (androgyn/unisex) oder 'unknown' wird nichts vorgeschlagen
    return ""
