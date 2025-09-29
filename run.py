# run.py
import os
import json
from app import create_app, db
from app.models import Vorlage, Gruppe, Eigenschaft

app = create_app()


def _create_vorlage_from_data(data, is_standard=False):
    """Hilfsfunktion, um eine Vorlage aus einem Dictionary in der DB zu erstellen."""
    if not Vorlage.query.filter_by(name=data["name"]).first():
        print(f"Erstelle Vorlage aus JSON: {data['name']}...")
        try:
            neue_vorlage = Vorlage(name=data["name"], is_standard=is_standard)
            db.session.add(neue_vorlage)
            db.session.flush()
            for gruppe_data in data.get("gruppen", []):
                gruppe = Gruppe(name=gruppe_data["name"], vorlage_id=neue_vorlage.id)
                db.session.add(gruppe)
                db.session.flush()
                for eigenschaft_data in gruppe_data.get("eigenschaften", []):
                    eigenschaft = Eigenschaft(
                        name=eigenschaft_data["name"],
                        datentyp=eigenschaft_data["datentyp"],
                        optionen=eigenschaft_data.get("optionen", ""),
                        gruppe_id=gruppe.id,
                    )
                    db.session.add(eigenschaft)
            db.session.commit()
        except Exception as e:
            print(f"Fehler beim Erstellen der Vorlage '{data['name']}': {e}")
            db.session.rollback()


def seed_templates_from_json():
    """Initialisiert alle Vorlagen aus den JSON-Dateien in der Datenbank."""
    with app.app_context():
        # 1. Standard-Vorlagen aus `data/standard_vorlagen`
        standard_vorlagen_pfad = "data/standard_vorlagen"
        if os.path.exists(standard_vorlagen_pfad):
            for filename in os.listdir(standard_vorlagen_pfad):
                if filename.endswith(".json"):
                    filepath = os.path.join(standard_vorlagen_pfad, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        _create_vorlage_from_data(data, is_standard=True)

        # 2. Benutzerdefinierte Vorlagen aus `data/user_vorlagen`
        user_vorlagen_pfad = "data/user_vorlagen"
        if os.path.exists(user_vorlagen_pfad):
            for filename in os.listdir(user_vorlagen_pfad):
                if filename.endswith(".json"):
                    filepath = os.path.join(user_vorlagen_pfad, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        _create_vorlage_from_data(data, is_standard=False)


def setup_database(app_instance):
    """Erstellt die Datenbank und füllt sie mit initialen Daten, falls nötig."""
    with app_instance.app_context():
        db.create_all()
        print("Prüfe auf Vorlagen aus JSON-Dateien...")
        seed_templates_from_json()


if __name__ == "__main__":
    setup_database(app)
    app.run(host="0.0.0.0", port=6061, debug=True)
