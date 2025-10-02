# app/services/titel_detector.py
"""
Dieses Modul extrahiert und formatiert akademische Titel gemäß DIN 5008
aus einem gegebenen Text.
"""
import re
from typing import List

# 1. Titel, die in der Anschrift vor dem Namen stehen (in der gewünschten Reihenfolge)
PRESTAGED_TITLES = [
    "Prof.",
    "Dr.-Ing.",
    "Dr. iur.",
    "Dr. med.",
    "Dr. oec.",
    "Dr. phil.",
    "Dr. rer. nat.",
    "Dr. rer. pol.",
    "Dr.",  # Dr. ohne Zusatz als Fallback
    "Dipl.-Ing.",
    "Dipl.-Kfm.",
    "Dipl.-Kffr.",
    "Dipl.-Hdl.",
    "Dipl.-Päd.",
    "Mag.",
    "Lic.",
]

# 2. Titel, die NICHT in die Anschrift gehören und ignoriert werden
IGNORED_TITLES = [
    "B. A.",
    "B. Sc.",
    "B. Eng.",
    "LL. B.",
    "B. F. A.",
    "B. Mus.",
    "B. Ed.",
    "M. A.",
    "M. Sc.",
    "M. Eng.",
    "LL. M.",
    "M. F. A.",
    "M. Mus.",
    "M. Ed.",
    "MBA",
    "M. Arch.",
    "Ph.D.",
]


def extract_titles(text: str) -> List[str]:
    """
    Extrahiert alle für die Anschrift relevanten Titel aus einem Text.

    Args:
        text: Ein String, der Titel enthalten könnte (z.B. "Prof. Dr. rer. nat. Max Mustermann").

    Returns:
        Eine Liste der gefundenen, sortierten Titel, die in der Anschrift verwendet werden.
    """
    if not text:
        return []

    found_titles = set()

    # Erstelle ein kombiniertes Pattern, um alle Titel zu finden.
    # Wir escapen Punkte und erstellen Wortgrenzen, um Teil-Matches zu vermeiden.
    all_known_titles = PRESTAGED_TITLES + IGNORED_TITLES

    # Sortiere die Titel nach Länge (absteigend), damit längere Titel zuerst gefunden werden
    # (z.B. "Dr.-Ing." vor "Dr.")
    sorted_titles = sorted(all_known_titles, key=len, reverse=True)

    for title in sorted_titles:
        # \b sorgt für eine Wortgrenze, re.escape behandelt z.B. den Punkt in "Dr."
        pattern = r"\b" + re.escape(title) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            # Füge den Titel in seiner korrekten Schreibweise hinzu
            found_titles.add(title)

    # Filtere nur die Titel, die in der Anschrift erlaubt sind
    relevant_titles = [t for t in found_titles if t in PRESTAGED_TITLES]

    # Sortiere die gefundenen Titel gemäß der vordefinierten Reihenfolge
    relevant_titles.sort(key=PRESTAGED_TITLES.index)

    # Sonderfall: Wenn "Dr.-Ing." etc. und "Dr." gefunden wurden,
    # behalte nur den spezifischeren Titel.
    if any(t.startswith("Dr.") and t != "Dr." for t in relevant_titles):
        if "Dr." in relevant_titles:
            relevant_titles.remove("Dr.")

    # Sonderfall Ph.D. -> Dr.
    if "Ph.D." in found_titles and "Dr." not in relevant_titles:
        relevant_titles.append("Dr.")

    return relevant_titles
