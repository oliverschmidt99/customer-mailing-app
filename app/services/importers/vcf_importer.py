# app/services/importers/vcf_importer.py
import vobject
import re


def parse_vcf(file_path):
    """Liest eine .vcf-Datei und gibt eine Liste mit einem Kontakt-Dictionary zurück."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        vcard_text = f.read()

    try:
        vcard = vobject.readOne(vcard_text)
    except Exception:
        # Manchmal haben VCFs Probleme, versuche es Zeile für Zeile
        vcard = vobject.readOne(vcard_text, ignoreUnreadable=True)

    data = {}
    if hasattr(vcard, "n"):
        data["Vorname"] = vcard.n.value.given
        data["Nachname"] = vcard.n.value.family
    if hasattr(vcard, "fn"):
        data["Name"] = vcard.fn.value
    if hasattr(vcard, "org"):
        data["Firma"] = vcard.org.value[0] if vcard.org.value else ""
    if hasattr(vcard, "title"):
        data["Position"] = vcard.title.value
    if hasattr(vcard, "tel"):
        for tel in vcard.tel_list:
            if "WORK" in tel.type_param:
                data["Telefon (geschäftlich)"] = tel.value
            elif "HOME" in tel.type_param:
                data["Telefon (privat)"] = tel.value
            elif "CELL" in tel.type_param:
                data["Mobilnummer"] = tel.value
    if hasattr(vcard, "email"):
        data["E-Mail"] = vcard.email.value
    if hasattr(vcard, "url"):
        data["Website"] = vcard.url.value
    if hasattr(vcard, "adr"):
        addr = vcard.adr.value
        street_line = addr.street

        # KORREKTUR: Versuche, Straße und Hausnummer zu trennen
        street_match = re.match(r"^(.+?)\s+([\d\w\s/.-]+)$", street_line)
        if street_match:
            data["Straße"] = street_match.group(1).strip().rstrip(",")
            data["Hausnummer"] = street_match.group(2).strip()
        else:
            data["Straße"] = street_line

        data["Ort"] = addr.city
        data["Postleitzahl"] = addr.code
        data["Land"] = addr.country

    return [data]  # In eine Liste packen, um konsistent mit anderen Importern zu sein
