# app/models.py
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()


class Vorlage(db.Model):
    __tablename__ = "vorlage"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    # NEU: Spalte, um Standard-Vorlagen zu kennzeichnen
    is_standard = db.Column(db.Boolean, default=False, nullable=False)

    gruppen = db.relationship(
        "Gruppe", backref="vorlage", lazy=True, cascade="all, delete-orphan"
    )
    kontakte = db.relationship(
        "Kontakt", backref="vorlage", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def eigenschaften(self):
        props = []
        for gruppe in self.gruppen:
            props.extend(gruppe.eigenschaften)
        return props


class Gruppe(db.Model):
    __tablename__ = "gruppe"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vorlage_id = db.Column(db.Integer, db.ForeignKey("vorlage.id"), nullable=False)
    eigenschaften = db.relationship(
        "Eigenschaft", backref="gruppe", lazy=True, cascade="all, delete-orphan"
    )


class Eigenschaft(db.Model):
    __tablename__ = "eigenschaft"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    datentyp = db.Column(db.String(50), nullable=False)
    optionen = db.Column(db.Text)
    gruppe_id = db.Column(db.Integer, db.ForeignKey("gruppe.id"), nullable=False)


class Kontakt(db.Model):
    __tablename__ = "kontakt"
    id = db.Column(db.Integer, primary_key=True)
    vorlage_id = db.Column(db.Integer, db.ForeignKey("vorlage.id"), nullable=False)
    daten = db.Column(db.Text, nullable=False, default="{}")

    def get_data(self):
        return json.loads(self.daten or "{}")

    def set_data(self, data_dict):
        self.daten = json.dumps(data_dict)
