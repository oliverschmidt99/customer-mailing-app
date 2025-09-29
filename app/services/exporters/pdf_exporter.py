# app/services/exporters/pdf_exporter.py
"""This module handles the generation of PDF files for contacts."""
from fpdf import FPDF

# --- Konstanten für Avery Zweckform 3424 Etiketten (in mm) ---
LABEL_WIDTH = 70
LABEL_HEIGHT = 37
LABELS_PER_ROW = 3
LABELS_PER_COL = 8

# Seitenränder des A4-Bogens
MARGIN_TOP = 10.5
MARGIN_LEFT = 4.75

# Abstand zwischen den Etiketten (nicht vorhanden bei 3424)
H_SPACING = 0
V_SPACING = 0

# --- NEU: Absenderadresse ---
SENDER_ADDRESS = "Rolf Janssen GmbH, Musterstraße 123, 26603 Aurich"


def _get_formatted_name(daten):
    """
    Formatiert den vollständigen Namen inklusive korrekt sortierter akademischer Titel.
    """
    # Listen zur Kategorisierung und Sortierung der Titel
    prestaged_order = [
        "Prof. Dr.",
        "Prof.",
        "Dr.-Ing.",
        "Dr. iur.",
        "Dr. med.",
        "Dr. oec.",
        "Dr. phil.",
        "Dr. rer. nat.",
        "Dr. rer. pol.",
        "Dipl.-Ing.",
        "Dipl.-Kfm.",
        "Dipl.-Kffr.",
        "Dipl.-Hdl.",
        "Dipl.-Päd.",
        "Mag.",
        "Lic.",
    ]

    postnominal_order = [
        "B. A.",
        "B. Ed.",
        "B. Eng.",
        "B. F. A.",
        "B. Mus.",
        "B. Sc.",
        "LL. B.",
        "M. A.",
        "M. Arch.",
        "M. Ed.",
        "M. Eng.",
        "M. F. A.",
        "M. Mus.",
        "M. Sc.",
        "LL. M.",
        "MBA",
        "Ph.D.",
    ]

    # KORREKTUR: Suche nach beiden möglichen Feldnamen für Titel
    titel_str = daten.get("Titel (akademisch)", daten.get("Titel", ""))

    if not titel_str:
        titel_list = []
    elif isinstance(titel_str, list):
        titel_list = titel_str
    else:
        titel_list = [t.strip() for t in titel_str.split(",")]

    prestaged = [t for t in titel_list if t in prestaged_order]
    postnominal = [t for t in titel_list if t in postnominal_order]

    # Titel gemäß ihrer definierten Reihenfolge sortieren
    prestaged.sort(
        key=lambda t: prestaged_order.index(t) if t in prestaged_order else 99
    )
    postnominal.sort(
        key=lambda t: postnominal_order.index(t) if t in postnominal_order else 99
    )

    # Namensteile zusammenfügen
    anrede = daten.get("Anrede", "")
    vorname = daten.get("Vorname", "")
    nachname = daten.get("Nachname", "")

    name_parts = [anrede]
    if prestaged:
        name_parts.extend(prestaged)
    name_parts.extend([vorname, nachname])
    if postnominal:
        # Nachgestellte Titel werden mit Komma abgetrennt
        name_parts.append(f", {', '.join(postnominal)}")

    return " ".join(filter(None, name_parts)).strip()


def generate_labels_pdf(kontakte):
    """
    Erstellt eine PDF-Datei mit Adressaufklebern im Format Avery Zweckform 3424.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False, margin=0)
    pdf.add_page()

    label_count = 0
    for kontakt in kontakte:
        daten = kontakt.get("daten", {})

        # Position des aktuellen Etiketts berechnen
        row = label_count % LABELS_PER_COL
        col = label_count // LABELS_PER_COL
        x = MARGIN_LEFT + col * (LABEL_WIDTH + H_SPACING)
        y = MARGIN_TOP + row * (LABEL_HEIGHT + V_SPACING)

        # --- Absenderzeile hinzufügen (kleinere Schrift) ---
        pdf.set_font("Arial", size=7)
        pdf.set_xy(x + 3, y + 2)  # Position etwas oberhalb der Hauptadresse
        safe_sender = SENDER_ADDRESS.encode("latin-1", "replace").decode("latin-1")
        pdf.cell(w=LABEL_WIDTH - 6, h=3, text=safe_sender, align="L")

        # --- Hauptadresse (normale Schrift) ---
        pdf.set_font("Arial", size=10)
        formatted_name = _get_formatted_name(daten)
        line1 = daten.get("Firmenname", "") or formatted_name

        line2 = ""
        if daten.get("Firmenname") and formatted_name:
            if formatted_name != daten.get("Anrede", ""):
                line2 = formatted_name

        strasse = daten.get("Straße", "")
        hausnummer = daten.get("Hausnummer", "")
        line3 = f"{strasse} {hausnummer}".strip()

        plz = daten.get("Postleitzahl", "")
        ort = daten.get("Ort", "")
        line4 = f"{plz} {ort}".strip()

        address_block = "\n".join(filter(None, [line1, line2, line3, line4]))

        # Position für den Adressblock (etwas nach unten verschoben)
        pdf.set_xy(x + 3, y + 7)
        safe_address_block = address_block.encode("latin-1", "replace").decode(
            "latin-1"
        )
        pdf.multi_cell(w=LABEL_WIDTH - 6, h=5, text=safe_address_block)

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
