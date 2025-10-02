# app/__init__.py
"""This module initializes the Flask application."""
import os
import json
from typing import List, Dict, Any

from flask import Flask
from flask_migrate import Migrate
from flask_executor import Executor
from .models import db


def get_attribute_suggestions() -> Dict[str, Any]:
    """Läd die Attribut-Vorschläge aus der JSON-Datei."""
    try:
        # Pfad korrigiert relativ zur App-Basis
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "data",
            "attribute_suggestions.json",
        )
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as err:
        print(f"Fehler beim Laden von data/attribute_suggestions.json: {err}")
        return {}


def get_selection_options() -> Dict[str, List[str]]:
    """Läd die globalen Auswahloptionen aus der JSON-Datei."""
    try:
        # Pfad korrigiert relativ zur App-Basis
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "data",
            "selection_options.json",
        )
        with open(filepath, "r", encoding="utf-8") as file:
            # Die Optionen werden in einem Dictionary bereitgestellt, das nach Attributname mappt
            options_list = json.load(file).get("options", [])
            options_dict = {
                item["name"]: [val.strip() for val in item["values"].split(",")]
                for item in options_list
            }
            return options_dict
    except (FileNotFoundError, json.JSONDecodeError) as err:
        print(f"Fehler beim Laden von data/selection_options.json: {err}")
        return {}


def get_config() -> Dict[str, Any]:
    """Läd die allgemeine Konfiguration aus der JSON-Datei."""
    try:
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data", "config.json"
        )
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as err:
        print(f"Fehler beim Laden von data/config.json: {err}")
        return {}


def create_app() -> Flask:
    """Erstellt und konfiguriert die Flask-Anwendung."""
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
        instance_relative_config=True,
    )

    # Konfiguration
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, "..", "instance")
    os.makedirs(instance_path, exist_ok=True)

    upload_path = os.path.join(basedir, "..", "upload_files")
    os.makedirs(upload_path, exist_ok=True)

    app.config["SECRET_KEY"] = "dein-super-geheimer-schluessel-hier"
    db_uri = f"sqlite:///{os.path.join(instance_path, 'kundenverwaltung.db')}"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = upload_path

    # Datenbank und Migration initialisieren
    db.init_app(app)
    Migrate(app, db)

    # Executor für Hintergrundaufgaben initialisieren
    Executor(app)

    with app.app_context():
        # pylint: disable=import-outside-toplevel, cyclic-import
        from .routes import main, vorlagen, kontakte, api, import_export, settings

        app.register_blueprint(main.bp)
        app.register_blueprint(vorlagen.bp)
        app.register_blueprint(kontakte.bp)
        app.register_blueprint(api.bp)
        app.register_blueprint(import_export.bp)
        app.register_blueprint(settings.bp)

        return app
