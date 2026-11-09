from datetime import date

from app.dateinamen import erstelle_dateinamen


def test_dateiname_enthaelt_datum_typ_und_firma():
    ergebnis = erstelle_dateinamen(
        date(2026, 1, 3),
        "Rechnungen",
        "Muster GmbH",
        ".pdf",
    )

    assert ergebnis == "260103_Rechnung_Muster GmbH.pdf"


def test_vertraege_werden_als_vertrag_benannt():
    ergebnis = erstelle_dateinamen(
        date(2026, 11, 9),
        "Verträge",
        "Beispiel AG",
        ".pdf",
    )

    assert ergebnis == "261109_Vertrag_Beispiel AG.pdf"


def test_eigene_kategorie_wird_uebernommen():
    ergebnis = erstelle_dateinamen(
        date(2026, 11, 9),
        "Weiterbildung",
        "Muster GmbH",
        ".jpg",
    )

    assert ergebnis == "261109_Weiterbildung_Muster GmbH.jpg"


def test_schraegstrich_wird_ersetzt_und_umlaut_bleibt_erhalten():
    ergebnis = erstelle_dateinamen(
        date(2026, 11, 9),
        "Rechnung",
        "Zürich/Partner",
        ".pdf",
    )

    assert ergebnis == "261109_Rechnung_Zürich-Partner.pdf"