import os
import re
from datetime import date

import pytest
from itsdangerous import SignatureExpired
from sqlalchemy.exc import SQLAlchemyError

from app import app, dokumentbearbeitung
from app.datenbank import Dokument, Kategorie, db

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)


@pytest.fixture
def bearbeitungs_client(monkeypatch):
    monkeypatch.setitem(app.config, "TESTING", True)
    with app.app_context():
        assert db.engine.url.host == "127.0.0.1"
        assert db.engine.url.port == 5433
        assert db.engine.url.database == "meinarchiv_test"
        assert db.engine.url.username == "meinarchiv_test"
        db.create_all()
        kategorie = Kategorie(name="Rechnungen")
        db.session.add(kategorie)
        db.session.flush()
        dokument = Dokument(
            dateiname="260103_Rechnung_Alt.pdf",
            firma="Alt GmbH",
            ablagedatum=date(2026, 1, 3),
            inhalt=b"Unveraenderte Datei",
            kategorie_id=kategorie.id,
            ist_entwurf=False,
        )
        db.session.add(dokument)
        db.session.commit()
        dokument_id = dokument.id
        kategorie_id = kategorie.id
    try:
        with app.test_client() as client:
            yield client, dokument_id, kategorie_id
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()


def _formular(client, dokument_id):
    antwort = client.get(f"/dokumente/{dokument_id}/kategorie")
    assert antwort.status_code == 200
    treffer = re.search(
        r'name="bestaetigung" value="([^"]+)"', antwort.get_data(as_text=True)
    )
    assert treffer is not None
    return treffer.group(1)


def _speichern(client, dokument_id, token, **werte):
    daten = {"firma": "Neue GmbH", "kategorie_id": "", "bestaetigung": token}
    daten.update(werte)
    return client.post(f"/dokumente/{dokument_id}/kategorie", data=daten)


def test_formular_zeigt_bestehende_angaben(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    html = client.get(f"/dokumente/{dokument_id}/kategorie").get_data(as_text=True)
    assert "Angaben bearbeiten" in html
    assert 'value="Alt GmbH"' in html
    assert "Rechnungen" in html
    assert "03.01.2026" in html
    assert 'name="ablagedatum"' not in html


def test_firma_kategorie_und_dateiname_werden_gemeinsam_gespeichert(
    bearbeitungs_client,
):
    client, dokument_id, _ = bearbeitungs_client
    with app.app_context():
        kategorie = Kategorie(name="Verträge")
        db.session.add(kategorie)
        db.session.commit()
        neue_id = kategorie.id
    token = _formular(client, dokument_id)
    antwort = _speichern(
        client,
        dokument_id,
        token,
        firma="  Muster GmbH  ",
        kategorie_id=str(neue_id),
        ablagedatum="2999-01-01",
    )
    assert antwort.status_code == 303
    assert antwort.headers["Location"].endswith(f"/dokumente/{dokument_id}")
    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)
        assert dokument.firma == "Muster GmbH"
        assert dokument.kategorie_id == neue_id
        assert dokument.ablagedatum == date(2026, 1, 3)
        assert dokument.dateiname == "260103_Vertrag_Muster GmbH.pdf"
        assert dokument.inhalt == b"Unveraenderte Datei"
    antwort = client.get(f"/dokumente/{dokument_id}/download")
    assert antwort.data == b"Unveraenderte Datei"
    assert "260103_Vertrag_Muster GmbH.pdf" in antwort.headers["Content-Disposition"]
    antwort.close()


@pytest.mark.parametrize("firma", ["", "   ", "X" * 121])
def test_ungueltige_firma_veraendert_keine_daten(bearbeitungs_client, firma):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    antwort = _speichern(client, dokument_id, token, firma=firma)
    assert antwort.status_code == 400
    assert "Bitte eine Firma" in antwort.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Dokument, dokument_id).firma == "Alt GmbH"


@pytest.mark.parametrize("kategorie_id", ["keine-zahl", "999999"])
def test_ungueltige_kategorie_behaelt_die_eingabe(bearbeitungs_client, kategorie_id):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    antwort = _speichern(client, dokument_id, token, kategorie_id=kategorie_id)
    assert antwort.status_code == 400
    assert 'value="Neue GmbH"' in antwort.get_data(as_text=True)
    with app.app_context():
        assert (
            db.session.get(Dokument, dokument_id).dateiname == "260103_Rechnung_Alt.pdf"
        )


@pytest.mark.parametrize("ablagedatum", ["", "kein-datum", "2999-01-01"])
def test_legacy_dokument_braucht_gueltiges_ablagedatum(
    bearbeitungs_client, ablagedatum
):
    client, dokument_id, _ = bearbeitungs_client
    with app.app_context():
        db.session.get(Dokument, dokument_id).ablagedatum = None
        db.session.commit()
    token = _formular(client, dokument_id)
    antwort = _speichern(client, dokument_id, token, ablagedatum=ablagedatum)
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id).ablagedatum is None


def test_legacy_datum_kann_einmal_ergaenzt_werden(bearbeitungs_client):
    client, dokument_id, kategorie_id = bearbeitungs_client
    with app.app_context():
        db.session.get(Dokument, dokument_id).ablagedatum = None
        db.session.commit()
    token = _formular(client, dokument_id)
    antwort = _speichern(
        client,
        dokument_id,
        token,
        ablagedatum="2025-12-01",
        kategorie_id=str(kategorie_id),
    )
    assert antwort.status_code == 303
    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)
        assert dokument.ablagedatum == date(2025, 12, 1)
        assert dokument.dateiname == "251201_Rechnung_Neue GmbH.pdf"


def test_ohne_kategorie_wird_dokument_im_dateinamen_verwendet(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    assert _speichern(client, dokument_id, token).status_code == 303
    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)
        assert dokument.kategorie_id is None
        assert dokument.dateiname == "260103_Dokument_Neue GmbH.pdf"


@pytest.mark.parametrize("token", ["", "manipuliert"])
def test_ungueltige_bestaetigung_speichert_nichts(bearbeitungs_client, token):
    client, dokument_id, _ = bearbeitungs_client
    assert _speichern(client, dokument_id, token).status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id).firma == "Alt GmbH"


def test_bestaetigung_ist_an_das_dokument_gebunden(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    with app.app_context():
        anderes = Dokument(dateiname="Anderes.pdf", inhalt=b"test", ist_entwurf=False)
        db.session.add(anderes)
        db.session.commit()
        andere_id = anderes.id
    antwort = _speichern(client, andere_id, token, ablagedatum="2026-01-01")
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, andere_id).firma is None


def test_veraltetes_formular_ueberschreibt_keine_neueren_angaben(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    with app.app_context():
        db.session.get(Dokument, dokument_id).firma = "Inzwischen geaendert"
        db.session.commit()
    antwort = _speichern(client, dokument_id, token)
    assert antwort.status_code == 409
    assert "inzwischen geändert" in antwort.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Dokument, dokument_id).firma == "Inzwischen geaendert"


def test_abgelaufenes_formular_speichert_nichts(bearbeitungs_client, monkeypatch):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)

    def abgelaufen(*args, **kwargs):
        raise SignatureExpired("Abgelaufen")

    monkeypatch.setattr(
        dokumentbearbeitung._bearbeitungs_bestaetigung, "loads", abgelaufen
    )
    assert _speichern(client, dokument_id, token).status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id).firma == "Alt GmbH"


def test_speicherfehler_rollt_alle_angaben_zurueck(bearbeitungs_client, monkeypatch):
    client, dokument_id, kategorie_id = bearbeitungs_client
    token = _formular(client, dokument_id)

    def fehlgeschlagen():
        raise SQLAlchemyError("Simulierter Commitfehler")

    with monkeypatch.context() as aenderungen:
        aenderungen.setattr(db.session, "commit", fehlgeschlagen)
        antwort = _speichern(client, dokument_id, token)
    assert antwort.status_code == 503
    with app.app_context():
        dokument = db.session.get(Dokument, dokument_id)
        assert dokument.firma == "Alt GmbH"
        assert dokument.kategorie_id == kategorie_id
        assert dokument.dateiname == "260103_Rechnung_Alt.pdf"


def test_unbekanntes_dokument_liefert_404(bearbeitungs_client):
    client, _, _ = bearbeitungs_client
    assert client.get("/dokumente/999999/kategorie").status_code == 404


def test_entwurf_wird_nicht_ueber_die_bearbeitung_archiviert(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    token = _formular(client, dokument_id)
    with app.app_context():
        db.session.get(Dokument, dokument_id).ist_entwurf = True
        db.session.commit()
    assert client.get(f"/dokumente/{dokument_id}/kategorie").status_code == 404
    assert _speichern(client, dokument_id, token).status_code == 404


def test_unterstuetzte_dateiendung_ist_erforderlich(bearbeitungs_client):
    client, dokument_id, _ = bearbeitungs_client
    with app.app_context():
        db.session.get(Dokument, dokument_id).dateiname = "Beleg.exe"
        db.session.commit()
    token = _formular(client, dokument_id)
    assert _speichern(client, dokument_id, token).status_code == 400
