# tree.py
"""
Ein Skript, um die Verzeichnisstruktur des Projekts in der Konsole auszugeben.
Ignoriert dabei vordefinierte Ordner und Dateiendungen für eine saubere Übersicht.
"""
import os

# --- Konfiguration ---
# Ordner, die bei der Anzeige ignoriert werden sollen
IGNORE_DIRS = {".git", ".vscode", "__pycache__", "venv", "simulations"}
# Dateiendungen, die ignoriert werden sollen
IGNORE_EXTS = {".fem", ".ans", ".png", ".json", ".csv", ".log"}


def print_tree(directory, prefix=""):
    """
    Gibt die Verzeichnisstruktur für einen gegebenen Pfad rekursiv in der Konsole aus.

    Args:
        directory (str): Der Startpfad für die Baumansicht.
        prefix (str): Das Präfix für die Einrückung (wird intern für die Rekursion verwendet).
    """
    try:
        # Filtere die Einträge im Verzeichnis basierend auf den IGNORE-Listen
        entries = [
            e
            for e in os.listdir(directory)
            if e not in IGNORE_DIRS
            and not (
                os.path.isfile(os.path.join(directory, e))
                and os.path.splitext(e)[1] in IGNORE_EXTS
            )
        ]
        entries.sort()
    except FileNotFoundError:
        print(f"Fehler: Verzeichnis nicht gefunden - {directory}")
        return

    for i, entry in enumerate(entries):
        full_path = os.path.join(directory, entry)
        # Wähle den passenden Konnektor für das letzte Element einer Ebene
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + entry)

        if os.path.isdir(full_path):
            # Passe das Präfix für die nächste Ebene an
            new_prefix = prefix + ("    " if i == len(entries) - 1 else "│   ")
            print_tree(full_path, new_prefix)


if __name__ == "__main__":
    print("Verzeichnisstruktur des Projekts (gefiltert):")
    print_tree(".")
