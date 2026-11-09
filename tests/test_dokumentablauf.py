import os
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from app import app
from app.datenbank import Dokument, Kategorie, db
from app.dateinamen import erstelle_dateinamen


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)


@pytest.fixture
def testumgebung(monkeypatch):
    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-schluessel")

    with app.app_context():
        # Nur die ausdrücklich vorgesehene Testdatenbank verwenden.
        assert db.engine.url.host == "127.0.0.1"
        assert db.engine.url.port == 5433
        assert db.engine.url.database == "meinarchiv_test"
        assert db.engine.url.username == "meinarchiv_test"

        db.create_all()

        kategorie = Kategorie(name="Rechnung")
        db.session.add(kategorie)
        db.session.commit()
        kategorie_id = kategorie.id

    try:
        with app.test_client() as client:
            yield client, kategorie_id
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_upload_analyse_bestaetigung_und_download(
    testumgebung, monkeypatch
):
    client, kategorie_id = testumgebung
    dateiinhalt = b"Testinhalt einer Rechnung"

    erkennung = MagicMock(
        return_value={
            "kategorie": "Rechnung",
            "firma": "Muster GmbH",
        }
    )
    monkeypatch.setattr("app.erkenne_dokument", erkennung)

    # 1. Datei hochladen.
    antwort = client.post(
        "/dokumente/vorbereiten",
        data={
            "dokument": (
                BytesIO(dateiinhalt),
                "rechnung.pdf",
            ),
        },
    )

    assert antwort.status_code == 303
    analyse_url = antwort.headers["Location"]
    dokument_id = int(analyse_url.split("/")[-2])

    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)
        assert dokument.ist_entwurf is True
        assert dokument.inhalt == dateiinhalt

    # 2. Ohne Freigabe darf keine KI-Anfrage erfolgen.
    antwort = client.post(analyse_url, data={})

    assert antwort.status_code == 400
    erkennung.assert_not_called()

    # 3. Mit Freigabe die simulierte Analyse ausführen.
    antwort = client.post(
        analyse_url,
        data={"freigabe": "ja"},
    )

    assert antwort.status_code == 200
    assert "Muster GmbH" in antwort.get_data(as_text=True)
    erkennung.assert_called_once_with(
        dateiinhalt,
        ".pdf",
        ["Rechnung"],
    )

    # 4. Erkannte Angaben bestätigen.
    heute = datetime.now(ZoneInfo("Europe/Zurich")).date()

    antwort = client.post(
        f"/dokumente/{dokument_id}/ki-uebernehmen",
        data={
            "kategorie_id": str(kategorie_id),
            "firma": "Muster GmbH",
        },
    )

    assert antwort.status_code == 303

    erwarteter_name = erstelle_dateinamen(
        heute,
        "Rechnung",
        "Muster GmbH",
        ".pdf",
    )

    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)

        assert dokument.ist_entwurf is False
        assert dokument.kategorie_id == kategorie_id
        assert dokument.firma == "Muster GmbH"
        assert dokument.ablagedatum == heute
        assert dokument.dateiname == erwarteter_name

    # 5. Dokument unter dem erzeugten Namen herunterladen.
    antwort = client.get(
        f"/dokumente/{dokument_id}/download"
    )

    assert antwort.status_code == 200
    assert antwort.data == dateiinhalt
    assert erwarteter_name in antwort.headers["Content-Disposition"]
    antwort.close()