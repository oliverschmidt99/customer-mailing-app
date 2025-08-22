# app.py
import os
import re
import subprocess
import tempfile
import shutil
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from src.models import db, Mitarbeiter, Kunde, Weihnachtspost
from sqlalchemy import or_
import csv
import io

# -- Konfiguration --
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"msg"}
BACKUP_FOLDER = "backup"

STATUS_EMOJIS = {
    "Neu": "🆕",
    "In Bearbeitung": "🔧",
    "Erledigt": "✅",
    "Unklar": "❓",
    "Fehler": "⚠️",
    "Doppelt": "🔁",
    "Warten": "⏳",
    "Abgelehnt": "🚫",
    "Inaktiv": "⏸️",
}
STATUS_OPTIONEN = list(STATUS_EMOJIS.keys())

PASTEL_COLORS = [
    "#FFADAD",
    "#FFD6A5",
    "#FDFFB6",
    "#CAFFBF",
    "#9BF6FF",
    "#A0C4FF",
    "#BDB2FF",
    "#FFC6FF",
]

app = Flask(__name__, static_folder="static")

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, "instance")
os.makedirs(instance_path, exist_ok=True)
backup_path = os.path.join(basedir, BACKUP_FOLDER)
os.makedirs(backup_path, exist_ok=True)

app.config["SECRET_KEY"] = "dein-super-geheimer-schluessel-hier"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(instance_path, 'weihnachtspost.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
db.init_app(app)


def backup_database():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"weihnachtspost_{timestamp}.db.bak"
    source_db = os.path.join(instance_path, "weihnachtspost.db")
    backup_filepath = os.path.join(backup_path, backup_filename)
    try:
        shutil.copy2(source_db, backup_filepath)
        flash(f"Datenbank-Backup erfolgreich erstellt: {backup_filename}", "success")
    except Exception as e:
        flash(f"Fehler beim Erstellen des Backups: {e}", "danger")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_vcard_text(text):
    data = {}
    patterns = {
        "vorname": r"(?:First Name|Vorname):\s*(.+)",
        "nachname": r"(?:Last Name|Nachname):\s*(.+)",
        "anrede": r"(?:Full Name|Name).*?(Herr|Frau)",
        "funktion": r"(?:Job Title|Funktion):\s*(.+)",
        "firma1": r"(?:Company|Firma):\s*(.+)",
        "telefon_beruflich": r"(?:Business|Telefon Geschäftlich):\s*([+\d\s()/.-]+)",
        "telefon_privat": r"(?:Home|Telefon Privat):\s*([+\d\s()/.-]+)",
        "mobil_telefon": r"(?:Mobile|Mobiltelefon):\s*([+\d\s()/.-]+)",
        "faxnummer": r"(?:Fax|Faxnummer):\s*([+\d\s()/.-]+)",
        "email": r"(?:Email|E-Mail Address):\s*([\w\.-]+@[\w\.-]+)",
    }
    for key, pattern in patterns.items():
        if match := re.search(pattern, text, re.IGNORECASE):
            data[key] = match.group(1).strip()
    if match := re.search(
        r"(?:Business Address|Geschäftsadresse):\s*(.*)", text, re.IGNORECASE
    ):
        addr = match.group(1).strip().replace("\r\n", " ")
        if addr_match := re.match(r"(.+?)\s+(\d{4,5})\s+(.+)", addr):
            data["strasse"], data["postleitzahl"], data["ort"] = (
                addr_match.group(1).strip(),
                addr_match.group(2).strip(),
                addr_match.group(3).strip(),
            )
        else:
            data["strasse"] = addr
    if match := re.search(r"Notes:\s*(.*)", text, re.DOTALL | re.IGNORECASE):
        data["anmerkungen"] = match.group(1).strip()
    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/verwaltung")
def verwaltung():
    mitarbeiter_liste = Mitarbeiter.query.all()
    kunden_liste = Kunde.query.all()
    return render_template(
        "verwaltung.html",
        mitarbeiter=mitarbeiter_liste,
        kunden=kunden_liste,
        pastel_colors=PASTEL_COLORS,
        status_emojis=STATUS_EMOJIS,
        status_optionen=STATUS_OPTIONEN,
        jahr=datetime.now().year,
    )


@app.route("/uebersicht")
def uebersicht():
    query = db.session.query(Kunde)
    mitarbeiter_id, post_art, status = (
        request.args.get("mitarbeiter_id"),
        request.args.get("post_art"),
        request.args.get("status"),
    )
    jahr = request.args.get("jahr", datetime.now().year, type=int)
    if mitarbeiter_id:
        query = query.filter(Kunde.mitarbeiter_id == mitarbeiter_id)
    if status:
        query = query.filter(Kunde.status == status)
    if post_art:
        query = query.join(Weihnachtspost).filter(Weihnachtspost.jahr == jahr)
        conditions = {
            "postkarte": Weihnachtspost.postkarte == True,
            "kalender": Weihnachtspost.kalender == True,
            "email_versand": Weihnachtspost.email_versand == True,
            "speziell": Weihnachtspost.speziell == True,
        }
        if post_art in conditions:
            query = query.filter(conditions[post_art])
    return render_template(
        "uebersicht.html",
        kunden=query.all(),
        mitarbeiter_liste=Mitarbeiter.query.all(),
        status_optionen=STATUS_OPTIONEN,
        status_emojis=STATUS_EMOJIS,
        aktiver_mitarbeiter=mitarbeiter_id,
        aktive_post_art=post_art,
        aktiver_status=status,
        aktives_jahr=jahr,
    )


@app.route("/export")
def export_page():
    query = db.session.query(Kunde)
    mitarbeiter_id, status, post_art = (
        request.args.get("mitarbeiter_id"),
        request.args.get("status"),
        request.args.get("post_art"),
    )
    jahr = request.args.get("jahr", type=int, default=datetime.now().year)
    if mitarbeiter_id:
        query = query.filter(Kunde.mitarbeiter_id == mitarbeiter_id)
    if status:
        query = query.filter(Kunde.status == status)
    if post_art:
        query = query.join(Weihnachtspost).filter(Weihnachtspost.jahr == jahr)
        conditions = {
            "postkarte": Weihnachtspost.postkarte == True,
            "kalender": Weihnachtspost.kalender == True,
            "email_versand": Weihnachtspost.email_versand == True,
            "speziell": Weihnachtspost.speziell == True,
        }
        if post_art in conditions:
            query = query.filter(conditions[post_art])
    return render_template(
        "export.html",
        kunden=query.all(),
        mitarbeiter_liste=Mitarbeiter.query.all(),
        status_optionen=STATUS_OPTIONEN,
        status_emojis=STATUS_EMOJIS,
        aktiver_mitarbeiter=mitarbeiter_id,
        aktive_post_art=post_art,
        aktiver_status=status,
        aktives_jahr=jahr,
    )


@app.route("/export/csv")
def export_csv():
    query = db.session.query(Kunde)
    mitarbeiter_id, status, post_art = (
        request.args.get("mitarbeiter_id"),
        request.args.get("status"),
        request.args.get("post_art"),
    )
    jahr = request.args.get("jahr", type=int, default=datetime.now().year)
    if mitarbeiter_id:
        query = query.filter(Kunde.mitarbeiter_id == mitarbeiter_id)
    if status:
        query = query.filter(Kunde.status == status)
    if post_art:
        query = query.join(Weihnachtspost).filter(Weihnachtspost.jahr == jahr)
        conditions = {
            "postkarte": Weihnachtspost.postkarte == True,
            "kalender": Weihnachtspost.kalender == True,
            "email_versand": Weihnachtspost.email_versand == True,
            "speziell": Weihnachtspost.speziell == True,
        }
        if post_art in conditions:
            query = query.filter(conditions[post_art])
    kunden_liste = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "ID",
        "Status",
        "Mitarbeiter",
        "Anrede",
        "Titel",
        "Vorname",
        "Nachname",
        "Firma",
        "Straße",
        "PLZ",
        "Ort",
        "Land",
        "E-Mail",
        "Telefon",
    ]
    writer.writerow(headers)
    for kunde in kunden_liste:
        row = [
            kunde.id,
            kunde.status,
            (
                f"{kunde.mitarbeiter.vorname} {kunde.mitarbeiter.nachname}"
                if kunde.mitarbeiter
                else ""
            ),
            kunde.anrede,
            kunde.titel,
            kunde.vorname,
            kunde.nachname,
            kunde.firma1,
            kunde.strasse,
            kunde.postleitzahl,
            kunde.ort,
            kunde.land,
            kunde.email,
            kunde.telefon_beruflich,
        ]
        writer.writerow(row)
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f'kunden_export_{datetime.now().strftime("%Y-%m-%d")}.csv',
    )


@app.route("/mitarbeiter/neu", methods=["POST"])
def mitarbeiter_neu():
    neuer_mitarbeiter = Mitarbeiter(**request.form)
    db.session.add(neuer_mitarbeiter)
    db.session.commit()
    backup_database()
    flash("Mitarbeiter erfolgreich hinzugefügt!", "success")
    return redirect(url_for("verwaltung"))


@app.route("/mitarbeiter/bearbeiten/<int:id>")
def mitarbeiter_bearbeiten(id):
    return render_template(
        "mitarbeiter_bearbeiten.html",
        mitarbeiter=Mitarbeiter.query.get_or_404(id),
        pastel_colors=PASTEL_COLORS,
    )


@app.route("/mitarbeiter/update/<int:id>", methods=["POST"])
def mitarbeiter_update(id):
    mitarbeiter = Mitarbeiter.query.get_or_404(id)
    for key, value in request.form.items():
        setattr(mitarbeiter, key, value)
    db.session.commit()
    backup_database()
    flash("Mitarbeiter erfolgreich aktualisiert!", "success")
    return redirect(url_for("verwaltung"))


@app.route("/mitarbeiter/loeschen/<int:id>", methods=["POST"])
def mitarbeiter_loeschen(id):
    db.session.delete(Mitarbeiter.query.get_or_404(id))
    db.session.commit()
    backup_database()
    flash("Mitarbeiter gelöscht.", "success")
    return redirect(url_for("verwaltung"))


@app.route("/kunden/erstellen", methods=["POST"])
def kunde_erstellen():
    neuer_kunde = Kunde()
    for key, value in request.form.items():
        if hasattr(Kunde, key):
            setattr(neuer_kunde, key, value)
    db.session.add(neuer_kunde)
    db.session.flush()
    post_eintrag = Weihnachtspost(
        kunde_id=neuer_kunde.id,
        jahr=datetime.now().year,
        postkarte="postkarte" in request.form,
        kalender="kalender" in request.form,
        email_versand="email_versand" in request.form,
        speziell="speziell" in request.form,
    )
    db.session.add(post_eintrag)
    db.session.commit()
    backup_database()
    flash("Kunde erfolgreich erstellt!", "success")
    return redirect(url_for("verwaltung"))


@app.route("/kunden/bearbeiten/<int:id>")
def kunde_bearbeiten(id):
    return render_template(
        "kunde_bearbeiten.html",
        kunde=Kunde.query.get_or_404(id),
        mitarbeiter=Mitarbeiter.query.all(),
        status_optionen=STATUS_OPTIONEN,
        status_emojis=STATUS_EMOJIS,
    )


@app.route("/kunden/update/<int:id>", methods=["POST"])
def kunde_update(id):
    kunde = Kunde.query.get_or_404(id)
    form_data = request.form.to_dict()
    if "mitarbeiter_id" in form_data and not form_data["mitarbeiter_id"]:
        kunde.mitarbeiter_id = None
        del form_data["mitarbeiter_id"]
    for key, value in form_data.items():
        setattr(kunde, key, value)
    db.session.commit()
    backup_database()
    flash("Kunde erfolgreich aktualisiert!", "success")
    return redirect(url_for("verwaltung"))


@app.route("/kunden/loeschen/<int:id>", methods=["POST"])
def kunde_loeschen(id):
    db.session.delete(Kunde.query.get_or_404(id))
    db.session.commit()
    backup_database()
    flash("Kunde erfolgreich gelöscht!", "success")
    return redirect(url_for("verwaltung"))


@app.route("/kunde/<int:kunde_id>/weihnachtspost")
def weihnachtspost_verwalten(kunde_id):
    kunde = Kunde.query.get_or_404(kunde_id)
    jahr = request.args.get("jahr", datetime.now().year, type=int)
    post_eintrag = Weihnachtspost.query.filter_by(kunde_id=kunde.id, jahr=jahr).first()
    return render_template(
        "weihnachtspost.html", kunde=kunde, post_eintrag=post_eintrag, jahr=jahr
    )


@app.route("/kunde/<int:kunde_id>/weihnachtspost/speichern", methods=["POST"])
def weihnachtspost_speichern(kunde_id):
    jahr = request.form.get("jahr", type=int)
    post_eintrag = Weihnachtspost.query.filter_by(kunde_id=kunde_id, jahr=jahr).first()
    if not post_eintrag:
        post_eintrag = Weihnachtspost(kunde_id=kunde_id, jahr=jahr)
        db.session.add(post_eintrag)
    post_eintrag.postkarte = "postkarte" in request.form
    post_eintrag.kalender = "kalender" in request.form
    post_eintrag.email_versand = "email_versand" in request.form
    post_eintrag.speziell = "speziell" in request.form
    db.session.commit()
    backup_database()
    flash(f"Weihnachtspost-Auswahl für {jahr} gespeichert.", "success")
    return redirect(url_for("weihnachtspost_verwalten", kunde_id=kunde_id, jahr=jahr))


@app.route("/import/msg", methods=["POST"])
def upload_msg():
    files, mitarbeiter_id = request.files.getlist("msg_files"), request.form.get(
        "mitarbeiter_id"
    )
    if not mitarbeiter_id:
        flash("Bitte einen Mitarbeiter für den Import auswählen!", "danger")
        return redirect(url_for("verwaltung"))
    post_auswahl = {
        "postkarte": "postkarte" in request.form,
        "kalender": "kalender" in request.form,
        "email_versand": "email_versand" in request.form,
        "speziell": "speziell" in request.form,
    }
    erfolgreich, aktualisiert, fehler = 0, 0, 0
    temp_dir = tempfile.mkdtemp()
    try:
        for file in files:
            if not (file and allowed_file(file.filename)):
                continue
            msg_filepath = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(msg_filepath)
            subprocess.run(
                ["python", "-m", "extract_msg", "--out", temp_dir, msg_filepath],
                capture_output=True,
            )
            message_txt_path = next(
                (
                    os.path.join(r, f)
                    for r, _, fs in os.walk(temp_dir)
                    for f in fs
                    if f.lower() == "message.txt"
                ),
                None,
            )
            if not message_txt_path:
                fehler += 1
                continue
            with open(message_txt_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            data = parse_vcard_text(text)
            kunde = None
            if email := data.get("email"):
                kunde = Kunde.query.filter_by(email=email).first()
            if (
                not kunde
                and (vorname := data.get("vorname"))
                and (nachname := data.get("nachname"))
            ):
                kunde = Kunde.query.filter(
                    db.func.lower(Kunde.vorname) == vorname.lower(),
                    db.func.lower(Kunde.nachname) == nachname.lower(),
                ).first()
            if kunde:
                for key, value in data.items():
                    if value and not getattr(kunde, key, None):
                        setattr(kunde, key, value)
                aktualisiert += 1
            else:
                neuer_kunde = Kunde(mitarbeiter_id=mitarbeiter_id, status="Neu")
                for key, value in data.items():
                    setattr(neuer_kunde, key, value)
                db.session.add(neuer_kunde)
                db.session.flush()
                post_eintrag = Weihnachtspost(
                    kunde_id=neuer_kunde.id, jahr=datetime.now().year, **post_auswahl
                )
                db.session.add(post_eintrag)
                erfolgreich += 1
            os.remove(message_txt_path)
            for item in os.listdir(temp_dir):
                if item.startswith(secure_filename(file.filename).rsplit(".", 1)[0]):
                    shutil.rmtree(os.path.join(temp_dir, item))
        db.session.commit()
        backup_database()
    except Exception as e:
        db.session.rollback()
        print(f"Schwerwiegender Fehler beim Import: {e}")
        flash(f"Ein Fehler ist aufgetreten: {e}", "danger")
        fehler += len(files) - (erfolgreich + aktualisiert)
    finally:
        shutil.rmtree(temp_dir)
    flash(
        f"{erfolgreich} neu importiert, {aktualisiert} aktualisiert, {fehler} Fehler.",
        "info",
    )
    return redirect(url_for("verwaltung"))


@app.route("/weihnachtspost/copy-previous-year", methods=["POST"])
def copy_previous_year_post():
    current_year, previous_year = datetime.now().year, datetime.now().year - 1
    previous_year_entries = Weihnachtspost.query.filter_by(jahr=previous_year).all()
    copied_count = 0
    for entry in previous_year_entries:
        if not Weihnachtspost.query.filter_by(
            kunde_id=entry.kunde_id, jahr=current_year
        ).first():
            new_entry = Weihnachtspost(
                kunde_id=entry.kunde_id,
                jahr=current_year,
                postkarte=entry.postkarte,
                kalender=entry.kalender,
                email_versand=entry.email_versand,
                speziell=entry.speziell,
            )
            db.session.add(new_entry)
            copied_count += 1
    if copied_count > 0:
        db.session.commit()
        backup_database()
        flash(
            f"{copied_count} Post-Einträge vom Vorjahr wurden für {current_year} übernommen.",
            "success",
        )
    else:
        flash("Keine neuen Post-Einträge zum Kopieren vom Vorjahr gefunden.", "info")
    return redirect(url_for("uebersicht", jahr=current_year))


@app.route("/settings")
def settings():
    return render_template("settings.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(port=6060, debug=True)
