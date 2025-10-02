# app/models.py
"""This module defines the database models for the application."""
import json
from typing import Dict, Any

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Vorlage(db.Model):
    """Definiert die Struktur eines Kontakttyps."""

    __tablename__ = "vorlage"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_standard = db.Column(db.Boolean, default=False, nullable=False)

    gruppen = db.relationship(
        "Gruppe", backref="vorlage", lazy=True, cascade="all, delete-orphan"
    )
    kontakte = db.relationship(
        "Kontakt", backref="vorlage", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def eigenschaften(self):
        """Gibt eine flache Liste aller Eigenschaften dieser Vorlage zurück."""
        props = []
        for gruppe in self.gruppen:
            props.extend(gruppe.eigenschaften)
        return props


class Gruppe(db.Model):
    """Definiert eine logische Gruppe von Eigenschaften innerhalb einer Vorlage."""

    __tablename__ = "gruppe"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vorlage_id = db.Column(db.Integer, db.ForeignKey("vorlage.id"), nullable=False)
    eigenschaften = db.relationship(
        "Eigenschaft", backref="gruppe", lazy=True, cascade="all, delete-orphan"
    )


class Eigenschaft(db.Model):
    """Definiert ein einzelnes Datenfeld innerhalb einer Gruppe."""

    __tablename__ = "eigenschaft"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    datentyp = db.Column(db.String(50), nullable=False)
    optionen = db.Column(db.Text)
    gruppe_id = db.Column(db.Integer, db.ForeignKey("gruppe.id"), nullable=False)
    # NEUES FELD für Mehrfachauswahl
    allow_multiselect = db.Column(db.Boolean, default=False, nullable=False)


class Kontakt(db.Model):
    """Stellt einen tatsächlichen Kontakt-Eintrag dar."""

    __tablename__ = "kontakt"
    id = db.Column(db.Integer, primary_key=True)
    vorlage_id = db.Column(db.Integer, db.ForeignKey("vorlage.id"), nullable=False)
    daten = db.Column(db.Text, nullable=False, default="{}")

    # NEUES FELD für den rohen Import-Inhalt
    import_raw_content = db.Column(db.Text, nullable=True)

    # NEUES FELD für die Quittierung von Validierungsfehlern
    validation_acknowledged = db.Column(db.Boolean, default=False, nullable=False)

    # Felder für performante Suche/Anzeige
    vorname = db.Column(db.String(100))
    nachname = db.Column(db.String(100))
    firma = db.Column(db.String(100))

    def get_data(self) -> Dict[str, Any]:
        """Gibt die gespeicherten JSON-Daten als Python-Dictionary zurück."""
        return json.loads(self.daten or "{}")

    def set_data(self, data_dict: Dict[str, Any]):
        """Speichert das Python-Dictionary als JSON und aktualisiert die Suchfelder."""
        # Konvertiere Listen (von Multi-Selects) in kommaseparierte Strings
        for key, value in data_dict.items():
            if isinstance(value, list):
                data_dict[key] = ", ".join(map(str, value))

        # Aktualisiere die Suchfelder basierend auf den Daten
        self.vorname = data_dict.get("Vorname", data_dict.get("First Name", ""))
        self.nachname = data_dict.get("Nachname", data_dict.get("Last Name", ""))
        # KORREKTUR: Tippfehler von data_get zu data_dict.get behoben
        self.firma = data_dict.get("Firma", data_dict.get("Company", ""))
        self.daten = json.dumps(data_dict)
