# app/services/exporters/pdf_exporter.py
"""This module handles the generation of PDF files for contacts."""
import os
from fpdf import FPDF
from ... import (
    get_config,
)

# KORREKTUR: Konstanten exakt nach deinen Vorgaben
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
    titel_str = daten.get("Titel (akademisch)", daten.get("Titel", ""))
    anrede = daten.get("Anrede", "")
    vorname = daten.get("Vorname", "")
    nachname = daten.get("Nachname", "")

    name_parts = [anrede, titel_str, vorname, nachname]
    return " ".join(filter(None, name_parts)).strip()


def _build_address_block(template, daten):
    """Ersetzt Platzhalter in einer Vorlage mit Kontaktdaten."""

    placeholders = {
        "{firmenname}": daten.get("Firmenname", ""),
        "{anrede}": daten.get("Anrede", ""),
        "{titel}": daten.get("Titel (akademisch)", daten.get("Titel", "")),
        "{vorname}": daten.get("Vorname", ""),
        "{nachname}": daten.get("Nachname", ""),
        "{name_komplett}": _get_formatted_name(daten),
        "{strasse}": daten.get("Straße", ""),
        "{hausnummer}": daten.get("Hausnummer", ""),
        "{plz}": daten.get("Postleitzahl", ""),
        "{ort}": daten.get("Ort", ""),
        "{land}": daten.get("Land", ""),
    }

    address_block = template
    for key, value in placeholders.items():
        address_block = address_block.replace(key, str(value))

    return "\n".join(
        line.strip() for line in address_block.splitlines() if line.strip()
    )


def generate_labels_pdf(kontakte):
    """
    Erstellt eine PDF-Datei mit Adressaufklebern basierend auf benutzerdefinierten Formaten.
    """
    config = get_config()
    sender_address = config.get("sender_address", "Standard Absender")
    logo_path = config.get("logo_path")
    logo_exists = logo_path and os.path.exists(logo_path)

    sender_font_size = config.get("export_sender_font_size", 7)
    logo_size = config.get("export_logo_size", 8)
    recipient_font_size = config.get("export_recipient_font_size", 10)

    # Lade Ausrichtungs-Einstellungen (L, C, R)
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
        x = MARGIN_LEFT + col * (LABEL_WIDTH + H_SPACING)
        y = MARGIN_TOP + row * (LABEL_HEIGHT + V_SPACING)

        pdf.set_font("Arial", size=sender_font_size)
        sender_x, sender_y = x + 3, y + 2
        safe_sender = sender_address.encode("latin-1", "replace").decode("latin-1")

        if logo_exists:
            text_width = LABEL_WIDTH - logo_size - 6
            pdf.set_xy(sender_x, sender_y)
            pdf.multi_cell(w=text_width, h=3, text=safe_sender, align=sender_align)

            logo_x = x + LABEL_WIDTH - logo_size - 3
            pdf.image(logo_path, x=logo_x, y=sender_y, h=logo_size)
        else:
            pdf.set_xy(sender_x, sender_y)
            pdf.multi_cell(w=LABEL_WIDTH - 6, h=3, text=safe_sender, align=sender_align)

        line_y = y + 12
        pdf.set_draw_color(180, 180, 180)
        pdf.line(x1=sender_x, y1=line_y, x2=x + LABEL_WIDTH - 3, y2=line_y)

        pdf.set_font("Arial", size=recipient_font_size)

        template = (
            config.get("address_format_company")
            if daten.get("Firmenname")
            else config.get("address_format_private")
        )
        if not template:  # Fallback
            template = (
                "{firmenname}\nz. Hd. {name_komplett}\n{strasse} {hausnummer}\n{plz} {ort}"
                if daten.get("Firmenname")
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
        if label_count >= LABELS_PER_ROW * LABELS_PER_COL:
            pdf.add_page()
            label_count = 0

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

                    if prop_value:
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
