# app/services/exporters/pdf_exporter.py
"""This module handles the generation of PDF files for contacts."""
import os
from fpdf import FPDF
from ... import (
    get_config,
)

# Konstanten exakt nach deinen Vorgaben
LABEL_WIDTH = 105
LABEL_HEIGHT = 48
LABELS_PER_ROW = 2
LABELS_PER_COL = 6
MARGIN_TOP = 4.5
MARGIN_LEFT = 0
H_SPACING = 0
V_SPACING = 0


def _get_formatted_name(daten):
    """
    Formatiert den vollständigen Namen inklusive korrekt sortierter akademischer Titel.
    """

    def get_clean(key):
        val = daten.get(key)
        return str(val).strip() if val and str(val).strip().lower() != "none" else ""

    titel_str = get_clean("Titel (akademisch)") or get_clean("Titel")
    anrede = get_clean("Anrede")
    vorname = get_clean("Vorname")
    nachname = get_clean("Nachname")

    name_parts = [anrede, titel_str, vorname, nachname]
    return " ".join(filter(None, name_parts)).strip()


def _build_address_block(template, daten):
    """Ersetzt Platzhalter in einer Vorlage mit Kontaktdaten."""

    def get_clean(key):
        val = daten.get(key)
        return str(val).strip() if val and str(val).strip().lower() != "none" else ""

    placeholders = {
        "{firmenname}": get_clean("Firmenname"),
        "{anrede}": get_clean("Anrede"),
        "{titel}": get_clean("Titel (akademisch)") or get_clean("Titel"),
        "{vorname}": get_clean("Vorname"),
        "{nachname}": get_clean("Nachname"),
        "{name_komplett}": _get_formatted_name(daten),
        "{strasse}": get_clean("Straße"),
        "{hausnummer}": get_clean("Hausnummer"),
        "{plz}": get_clean("Postleitzahl"),
        "{ort}": get_clean("Ort"),
        "{land}": get_clean("Land"),
    }

    address_block = template
    for key, value in placeholders.items():
        address_block = address_block.replace(key, value)

    cleaned_lines = []
    for line in address_block.splitlines():
        cleaned_line = " ".join(line.split())
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
    return "\n".join(cleaned_lines)


def generate_labels_pdf(kontakte):
    """
    Erstellt eine PDF-Datei mit Adressaufklebern basierend auf benutzerdefinierten Formaten.
    """
    config = get_config()
    sender_address = config.get("sender_address", "Standard Absender")
    logo_path = config.get("logo_path")
    logo_exists = logo_path and os.path.exists(logo_path)

    sender_font_size = config.get("export_sender_font_size", 7)
    logo_width = config.get("export_logo_size", 8)
    recipient_font_size = config.get("export_recipient_font_size", 10)

    sender_align = config.get("export_sender_alignment", "L")
    recipient_align = config.get("export_recipient_alignment", "L")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.add_page()

    label_count = 0
    for kontakt in kontakte:
        daten = kontakt.get("daten", {})

        row = label_count // LABELS_PER_ROW
        col = label_count % LABELS_PER_ROW

        if row >= LABELS_PER_COL:
            pdf.add_page()
            label_count = 0
            row, col = 0, 0

        x = MARGIN_LEFT + col * (LABEL_WIDTH + H_SPACING)
        y = MARGIN_TOP + row * (LABEL_HEIGHT + V_SPACING)

        pdf.set_font("Arial", size=sender_font_size)
        sender_x, sender_y_base = x + 3, y + 2
        safe_sender = sender_address.encode("latin-1", "replace").decode("latin-1")

        # KORREKTUR: Logik zur vertikalen Zentrierung des Textes, unabhängig vom Logo
        sender_area_height = 10  # Der Bereich ist 10mm hoch (von y+2 bis y+12)

        # Bestimme die Textbreite basierend auf der Logo-Existenz
        if logo_exists:
            text_width = LABEL_WIDTH - logo_width - 6
        else:
            text_width = LABEL_WIDTH - 6

        # Berechne die Höhe des Text-Blocks durch eine Simulation
        text_height = pdf.multi_cell(
            w=text_width, h=3, text=safe_sender, dry_run=True, align=sender_align
        )

        # Berechne den Y-Offset, um den Text im 10mm-Bereich zu zentrieren
        text_y_offset = (sender_area_height / 2) - (text_height / 2)
        if text_y_offset < 0:
            text_y_offset = 0  # Verhindert, dass der Text nach oben rutscht

        # Platziere den Text an der zentrierten Position
        pdf.set_xy(sender_x, sender_y_base + text_y_offset)
        pdf.multi_cell(w=text_width, h=3, text=safe_sender, align=sender_align)

        # Platziere das Logo (falls vorhanden) am oberen Rand des Absenderbereichs
        if logo_exists:
            try:
                logo_x = x + LABEL_WIDTH - logo_width - 3
                pdf.image(logo_path, x=logo_x, y=sender_y_base, w=logo_width)
            except Exception as e:
                print(f"WARNUNG: Logo konnte nicht verarbeitet werden. Fehler: {e}")

        # --- Weiterer Code bleibt unverändert ---
        line_y = y + 12
        pdf.set_draw_color(180, 180, 180)
        pdf.line(x1=sender_x, y1=line_y, x2=x + LABEL_WIDTH - 3, y2=line_y)

        pdf.set_font("Arial", size=recipient_font_size)

        template_key = (
            "address_format_company"
            if daten.get("Firmenname")
            and str(daten.get("Firmenname")).strip().lower() != "none"
            else "address_format_private"
        )
        template = config.get(template_key) or (
            "{firmenname}\nz. Hd. {name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}"
            if template_key == "address_format_company"
            else "{name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}"
        )

        address_block = _build_address_block(template, daten)
        pdf.set_xy(x + 3, line_y + 2)
        safe_address_block = address_block.encode("latin-1", "replace").decode(
            "latin-1"
        )
        pdf.multi_cell(
            w=LABEL_WIDTH - 6, h=5, text=safe_address_block, align=recipient_align
        )

        label_count += 1

    return bytes(pdf.output())


def generate_pdf(kontakte, vorlage_struktur):
    """
    Erstellt eine detaillierte PDF-Ansicht für jeden Kontakt.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for kontakt in kontakte:
        pdf.add_page()
        daten = kontakt["daten"]
        full_name = _get_formatted_name(daten) or daten.get("Firmenname", "")
        pdf.set_font("Arial", "B", 16)
        safe_full_name = full_name.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(0, 10, safe_full_name, ln=True, align="L")
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(10)

        for gruppe in vorlage_struktur["gruppen"]:
            properties_in_group = [
                e
                for e in gruppe["eigenschaften"]
                if e["name"] not in ["Titel (akademisch)", "Titel"]
            ]
            has_content = any(daten.get(e["name"]) for e in properties_in_group)

            if has_content:
                pdf.set_font("Arial", "B", 12)
                safe_group_name = (
                    gruppe["name"].encode("latin-1", "replace").decode("latin-1")
                )
                pdf.cell(0, 10, safe_group_name, ln=True, align="L")
                pdf.ln(2)

                for eigenschaft in properties_in_group:
                    prop_name = eigenschaft["name"]
                    prop_value = str(daten.get(prop_name, ""))

                    if prop_value and prop_value.lower() != "none":
                        start_x = pdf.get_x()
                        pdf.set_font("Arial", "B", 10)
                        safe_prop_name = prop_name.encode("latin-1", "replace").decode(
                            "latin-1"
                        )
                        pdf.cell(60, 8, safe_prop_name, align="L")
                        pdf.set_font("Arial", "", 10)
                        safe_prop_value = prop_value.encode(
                            "latin-1", "replace"
                        ).decode("latin-1")
                        value_width = pdf.w - pdf.l_margin - pdf.r_margin - 60
                        pdf.multi_cell(value_width, 8, safe_prop_value, align="L")
                        pdf.set_x(start_x)
                        pdf.ln(5)
                pdf.ln(5)

    return bytes(pdf.output())
