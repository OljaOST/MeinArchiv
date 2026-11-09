import re


def erstelle_dateinamen(ablagedatum, kategoriename, firma, endung):
    dokumenttypen = {
        "Rechnungen": "Rechnung",
        "Verträge": "Vertrag",
        "Vorträge": "Vortrag",
        "Versicherungen": "Versicherung",
    }

    dokumenttyp = dokumenttypen.get(kategoriename, kategoriename)

    ungueltige_zeichen = r'[<>:"/\\|?*\x00-\x1f_]'

    dokumenttyp = re.sub(
        ungueltige_zeichen, "-", dokumenttyp
    ).strip(" .-")

    firma = re.sub(
        ungueltige_zeichen, "-", firma
    ).strip(" .-")

    dokumenttyp = dokumenttyp or "Dokument"
    firma = firma or "Unbekannt"

    return f"{ablagedatum:%y%m%d}_{dokumenttyp}_{firma}{endung}"