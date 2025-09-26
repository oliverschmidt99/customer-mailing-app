# app/routes/kontakte.py
import json
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from sqlalchemy.orm import subqueryload
from sqlalchemy import or_
from ..models import db, Vorlage, Kontakt, Gruppe
from .. import get_attribute_suggestions, get_selection_options

bp = Blueprint("kontakte", __name__, url_prefix="/kontakte")


@bp.route("/")
def auflisten():
    """Zeigt die Kontaktübersicht an und lädt alle Vorlagen und Kontakte."""
    # KORRIGIERTE UND OPTIMIERTE DATENBANKABFRAGE
    vorlagen_query = (
        Vorlage.query.options(
            subqueryload(Vorlage.kontakte),
            subqueryload(Vorlage.gruppen).subqueryload(Gruppe.eigenschaften),
        )
        .order_by(Vorlage.name)
        .all()
    )

    vorlagen_data = []
    for v in vorlagen_query:
        vorlage_dict = {
            "id": v.id,
            "name": v.name,
            "eigenschaften": [
                {
                    "id": e.id,
                    "name": e.name,
                    "datentyp": e.datentyp,
                    "optionen": e.optionen,
                }
                for g in v.gruppen
                for e in g.eigenschaften
            ],
            "kontakte": [{"id": k.id, "daten": k.get_data()} for k in v.kontakte],
            "gruppen": [
                {
                    "id": g.id,
                    "name": g.name,
                    "eigenschaften": [
                        {
                            "id": e.id,
                            "name": e.name,
                            "datentyp": e.datentyp,
                            "optionen": e.optionen,
                        }
                        for e in g.eigenschaften
                    ],
                }
                for g in v.gruppen
            ],
        }
        vorlagen_data.append(vorlage_dict)

    return render_template(
        "kontakte_liste.html", vorlagen_for_json=json.dumps(vorlagen_data)
    )


@bp.route("/editor", methods=["GET", "POST"])
def editor():
    """Erlaubt das Bearbeiten oder Erstellen eines Kontakts basierend auf einer Vorlage."""
    kontakt_id = request.args.get("kontakt_id", type=int)
    vorlage_id = request.args.get("vorlage_id", type=int)

    # Lade benötigte Daten
    attribute_suggestions = get_attribute_suggestions()
    selection_options = get_selection_options()

    verknuepfungen = []

    # Hole den Kontakt oder die Vorlage
    if kontakt_id:
        kontakt = db.session.get(Kontakt, kontakt_id)
        # Handle case where kontakt might be None
        if kontakt is None:
            return redirect(url_for("vorlagen.verwalten"))

        vorlage = kontakt.vorlage
        action_url = url_for("kontakte.editor", kontakt_id=kontakt.id)

        # Extrahieren der Verknüpfungen für das Template-Rendering
        verknuepfung_ids = kontakt.get_data().get("Verknüpfungen", [])
        # Sicherstellen, dass die Liste nur ganze Zahlen enthält
        safe_ids = [i for i in verknuepfung_ids if isinstance(i, int)]
        if safe_ids:
            verknuepfungen = Kontakt.query.filter(Kontakt.id.in_(safe_ids)).all()

    elif vorlage_id:
        kontakt = None
        vorlage = db.session.get(Vorlage, vorlage_id)
        # Handle case where vorlage might be None
        if vorlage is None:
            return redirect(url_for("vorlagen.verwalten"))

        action_url = url_for("kontakte.editor", vorlage_id=vorlage.id)
    else:
        return redirect(url_for("vorlagen.verwalten"))

    if request.method == "POST":
        form_daten = request.form.to_dict()

        # Logik zum Parsen der dynamischen Formularfelder und Verknüpfungen
        kontakt_data_to_save = {}
        verknuepfung_ids = request.form.getlist("verknuepfung_ids")

        for key, value in form_daten.items():
            if key.startswith("attribute_key_"):
                # Finde den zugehörigen Wert
                name = value
                value_key = f"attribute_value_{name}"
                if value_key in form_daten:
                    kontakt_data_to_save[name] = form_daten[value_key]

        # Speichere Verknüpfungen als Attribut im Daten-JSON
        if verknuepfung_ids:
            kontakt_data_to_save["Verknüpfungen"] = [
                int(i) for i in verknuepfung_ids if i.isdigit()
            ]

        if kontakt:
            kontakt.set_data(kontakt_data_to_save)
        else:
            neuer_kontakt = Kontakt(vorlage_id=vorlage.id)
            neuer_kontakt.set_data(kontakt_data_to_save)
            db.session.add(neuer_kontakt)

        db.session.commit()
        return redirect(url_for("kontakte.auflisten"))

    vorlage_for_json = {
        "id": vorlage.id,
        "name": vorlage.name,
        "gruppen": [
            {
                "id": g.id,
                "name": g.name,
                "eigenschaften": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "datentyp": e.datentyp,
                        "optionen": e.optionen,
                    }
                    for e in g.eigenschaften
                ],
            }
            for g in vorlage.gruppen
        ],
    }
    kontakt_daten_for_json = kontakt.get_data() if kontakt else {}

    return render_template(
        "kontakt_editor.html",
        action_url=action_url,
        kontakt=kontakt,
        vorlage_for_json=json.dumps(vorlage_for_json),
        kontakt_daten_for_json=json.dumps(kontakt_daten_for_json),
        attribute_suggestions=attribute_suggestions,
        selection_options=selection_options,
        verknuepfungen=verknuepfungen,
    )


@bp.route("/api/kontakte/search", methods=["GET"])
def search_kontakte():
    """Sucht nach Kontakten anhand von Vorname, Nachname oder Firma für Verknüpfungen."""
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)

    if not query or len(query) < 2:
        return jsonify([])

    search_term = f"%{query}%"

    # Suche auf den dedizierten Spalten (vorname, nachname, firma)
    results = (
        Kontakt.query.filter(
            or_(
                Kontakt.vorname.ilike(search_term),
                Kontakt.nachname.ilike(search_term),
                Kontakt.firma.ilike(search_term),
            )
        )
        .limit(limit)
        .all()
    )

    # Formatiere die Ergebnisse für das Frontend
    formatted_results = []
    for kontakt in results:
        # Erzeuge einen sinnvollen Anzeigetext
        display_name = f"{kontakt.vorname} {kontakt.nachname}".strip()
        if kontakt.firma:
            display_name += f" ({kontakt.firma})"

        # Wenn kein Name existiert, zeige die ID
        if not display_name:
            display_name = f"Kontakt ID: {kontakt.id}"

        formatted_results.append({"id": kontakt.id, "text": display_name})

    return jsonify(formatted_results)


@bp.route("/loeschen/<int:kontakt_id>", methods=["POST"])
def loeschen(kontakt_id):
    """Löscht einen Kontakt."""
    kontakt = db.session.get(Kontakt, kontakt_id)
    if kontakt:
        db.session.delete(kontakt)
        db.session.commit()
    return redirect(url_for("kontakte.auflisten"))
