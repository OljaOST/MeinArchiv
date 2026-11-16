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

    dokumenttyp = re.sub(ungueltige_zeichen, "-", dokumenttyp).strip(" .-")

    firma = re.sub(ungueltige_zeichen, "-", firma).strip(" .-")

    dokumenttyp = dokumenttyp or "Dokument"
    firma = firma or "Unbekannt"

    return f"{ablagedatum:%y%m%d}_{dokumenttyp}_{firma}{endung}"


def dateiname_mit_endung(eingabe, endung):
    """Validiert einen eingegebenen Namen mit der bestehenden Dateiendung."""
    stamm = eingabe.strip()
    if endung and stamm.lower().endswith(endung.lower()):
        stamm = stamm[: -len(endung)]
    if (
        not stamm.strip(" .")
        or stamm.endswith((".", " "))
        or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', stamm)
        or len(stamm) + len(endung) > 255
    ):
        raise ValueError(
            "Gib einen gültigen Dokumentnamen ohne Pfad oder Sonderzeichen ein."
        )
    return stamm + endung
