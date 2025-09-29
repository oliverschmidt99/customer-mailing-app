# app/services/exporter_service.py
"""This service handles the selection of the correct exporter."""
from .exporters import csv_exporter, xlsx_exporter, pdf_exporter


def export_data(file_format, kontakte_data, vorlage_struktur):
    """
    Erkennt das gewünschte Exportformat und ruft die entsprechende Funktion auf.
    """
    eigenschaften = [
        e
        for g in vorlage_struktur.get("gruppen", [])
        for e in g.get("eigenschaften", [])
    ]

    if file_format == "csv":
        content = csv_exporter.generate_csv(kontakte_data, eigenschaften)
        mimetype = "text/csv"
    elif file_format == "xlsx":
        content = xlsx_exporter.generate_xlsx(kontakte_data, eigenschaften)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif file_format == "pdf":
        content = pdf_exporter.generate_pdf(kontakte_data, vorlage_struktur)
        mimetype = "application/pdf"
    # NEUE OPTION für Adressaufkleber
    elif file_format == "pdf-labels":
        content = pdf_exporter.generate_labels_pdf(kontakte_data)
        mimetype = "application/pdf"
    else:
        return None, None

    return content, mimetype
