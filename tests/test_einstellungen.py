import hashlib
import importlib
import json
import os
from datetime import date
from io import BytesIO
from pathlib import PurePosixPath
from types import SimpleNamespace
from unittest.mock import MagicMock
from zipfile import ZipFile

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.datenbank import Dokument, Kategorie, db

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)


@pytest.fixture
def einstellungs_client(monkeypatch):
    monkeypatch.setitem(app.config, "TESTING", True)
    with app.app_context():
        assert db.engine.url.host == "127.0.0.1"
        assert db.engine.url.port == 5433
        assert db.engine.url.database == "meinarchiv_test"
        assert db.engine.url.username == "meinarchiv_test"
        db.create_all()
    try:
        with app.test_client() as client:
            yield client
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()


def _beispieldaten():
    with app.app_context():
        kategorie = Kategorie(name="Rechnungen")
        db.session.add_all([kategorie, Kategorie(name="Leere Kategorie")])
        db.session.flush()
        erstes = Dokument(
            dateiname="Gleicher_Name.pdf",
            inhalt=b"Erster Inhalt",
            firma="Zürich & Partner",
            ablagedatum=date(2026, 1, 3),
            kategorie_id=kategorie.id,
            ist_entwurf=False,
        )
        zweites = Dokument(
            dateiname="Gleicher_Name.pdf",
            inhalt=b"Zweiter Inhalt",
            ist_entwurf=False,
        )
        entwurf = Dokument(
            dateiname="ENTWURF_GEHEIM.pdf",
            inhalt=b"Nicht exportieren",
            ist_entwurf=True,
        )
        db.session.add_all([erstes, zweites, entwurf])
        db.session.commit()
        return erstes.id, zweites.id, entwurf.id


def test_einstellungen_zeigen_statistik_ohne_schluessel_zu_verraten(
    einstellungs_client,
    monkeypatch,
):
    _beispieldaten()
    schluessel = "sk-dieser-geheime-testwert-darf-nicht-im-html-stehen"
    monkeypatch.setenv("OPENAI_API_KEY", schluessel)
    antwort = einstellungs_client.get("/einstellungen")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert 'id="status-dokumente">2</dd>' in html
    assert 'id="status-entwuerfe">1</dd>' in html
    assert "Schlüssel hinterlegt" in html
    assert schluessel not in html
    assert 'href="/export/dokumente"' in html


@pytest.mark.parametrize("schluessel", ["", "   "])
def test_fehlender_api_schluessel_wird_klar_angezeigt(
    einstellungs_client,
    monkeypatch,
    schluessel,
):
    monkeypatch.setenv("OPENAI_API_KEY", schluessel)
    antwort = einstellungs_client.get("/einstellungen")
    assert antwort.status_code == 200
    assert "Nicht eingerichtet" in antwort.get_data(as_text=True)


def test_leeres_archiv_hat_gueltigen_export(einstellungs_client):
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    with ZipFile(BytesIO(antwort.data)) as archiv:
        assert set(archiv.namelist()) == {"metadaten.json", "LIESMICH.txt"}
        daten = json.loads(archiv.read("metadaten.json"))
        assert daten["anzahl_dokumente"] == 0
        assert daten["dokumente"] == []
        assert daten["kategorien"] == []
    antwort.close()


def test_export_enthaelt_dateien_metadaten_und_keine_entwuerfe(einstellungs_client):
    erstes, zweites, entwurf = _beispieldaten()
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    assert antwort.mimetype == "application/zip"
    assert antwort.headers["Content-Disposition"].startswith("attachment;")
    assert "MeinArchiv-Export-" in antwort.headers["Content-Disposition"]
    assert antwort.headers["Cache-Control"] == "no-store"
    with ZipFile(BytesIO(antwort.data)) as archiv:
        daten = json.loads(archiv.read("metadaten.json"))
        assert daten["version"] == 1
        assert daten["anzahl_dokumente"] == 2
        assert {k["name"] for k in daten["kategorien"]} == {
            "Rechnungen",
            "Leere Kategorie",
        }
        dokumente = {d["id"]: d for d in daten["dokumente"]}
        assert set(dokumente) == {erstes, zweites}
        assert entwurf not in dokumente
        assert dokumente[erstes]["firma"] == "Zürich & Partner"
        assert dokumente[erstes]["ablagedatum"] == "2026-01-03"
        assert dokumente[erstes]["kategorie"] == "Rechnungen"
        assert dokumente[zweites]["kategorie"] is None
        assert dokumente[zweites]["ablagedatum"] is None
        assert dokumente[erstes]["archivpfad"] != dokumente[zweites]["archivpfad"]
        for dokument_id, inhalt in [
            (erstes, b"Erster Inhalt"),
            (zweites, b"Zweiter Inhalt"),
        ]:
            dokument = dokumente[dokument_id]
            assert archiv.read(dokument["archivpfad"]) == inhalt
            assert dokument["groesse_bytes"] == len(inhalt)
            assert dokument["sha256"] == hashlib.sha256(inhalt).hexdigest()
        assert "ENTWURF_GEHEIM.pdf" not in str(daten)
    antwort.close()


@pytest.mark.parametrize(
    "name",
    [
        "../../ausbruch.pdf",
        "..\\..\\ausbruch.pdf",
        "CON.pdf",
        "../..",
        "ä & Firma.pdf",
    ],
)
def test_exportpfade_bleiben_im_dokumentordner(einstellungs_client, name):
    with app.app_context():
        dokument = Dokument(dateiname=name, inhalt=b"test", ist_entwurf=False)
        db.session.add(dokument)
        db.session.commit()
        dokument_id = dokument.id
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    with ZipFile(BytesIO(antwort.data)) as archiv:
        daten = json.loads(archiv.read("metadaten.json"))
        eintrag = daten["dokumente"][0]
        pfad = PurePosixPath(eintrag["archivpfad"])
        assert not pfad.is_absolute()
        assert pfad.parts[:2] == ("dokumente", str(dokument_id))
        assert len(pfad.parts) == 3
        assert ".." not in pfad.parts
        assert eintrag["dateiname"] == name
        assert archiv.read(str(pfad)) == b"test"
    antwort.close()


def test_export_veraendert_keine_gespeicherten_daten(einstellungs_client):
    ids = _beispieldaten()
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    _ = antwort.data
    antwort.close()
    with app.app_context():
        assert [db.session.get(Dokument, i).dateiname for i in ids] == [
            "Gleicher_Name.pdf",
            "Gleicher_Name.pdf",
            "ENTWURF_GEHEIM.pdf",
        ]
        assert db.session.scalar(db.select(db.func.count(Kategorie.id))) == 2


def test_datenbankfehler_verhindert_irrefuehrende_statistik(
    einstellungs_client,
    monkeypatch,
):
    def fehlgeschlagen(*args, **kwargs):
        raise SQLAlchemyError("Simulierter Fehler")

    monkeypatch.setattr(db.session, "execute", fehlgeschlagen)
    antwort = einstellungs_client.get("/einstellungen")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 503
    assert "Die Archivdaten konnten nicht geladen werden" in html
    assert 'id="status-dokumente"' not in html
    assert 'href="/export/dokumente"' not in html


def test_exportfehler_liefert_keine_unvollstaendige_zip_datei(
    einstellungs_client,
    monkeypatch,
):
    def fehlgeschlagen(*args, **kwargs):
        raise SQLAlchemyError("Simulierter Fehler")

    monkeypatch.setattr(db.session, "execute", fehlgeschlagen)
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 503
    assert antwort.mimetype == "text/html"
    assert "Export nicht abgeschlossen" in antwort.get_data(as_text=True)


def test_status_und_export_loesen_keine_ki_anfrage_aus(
    einstellungs_client,
    monkeypatch,
):
    _beispieldaten()
    schluessel = "sk-geheim-nur-fuer-diesen-test"
    monkeypatch.setenv("OPENAI_API_KEY", schluessel)
    klient = MagicMock(side_effect=AssertionError("Keine KI-Anfrage erlaubt"))
    monkeypatch.setattr("app.OpenAI", klient)
    monkeypatch.setattr("app.ki.OpenAI", klient)
    assert einstellungs_client.get("/einstellungen").status_code == 200
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    with ZipFile(BytesIO(antwort.data)) as archiv:
        assert schluessel.encode() not in archiv.read("metadaten.json")
    antwort.close()
    klient.assert_not_called()


def test_grosser_export_bleibt_vollstaendig_und_schliesst_temporaere_datei(
    einstellungs_client,
    monkeypatch,
):
    modul = importlib.import_module("app.einstellungen")
    original = modul.tempfile.SpooledTemporaryFile
    dateien = []

    def temporaere_datei(*args, **kwargs):
        datei = original(*args, **kwargs)
        dateien.append(datei)
        return datei

    monkeypatch.setattr(
        modul, "tempfile", SimpleNamespace(SpooledTemporaryFile=temporaere_datei)
    )
    inhalt = os.urandom(9 * 1024 * 1024)
    with app.app_context():
        db.session.add(
            Dokument(
                dateiname="Grosse_Datei.pdf",
                inhalt=inhalt,
                ist_entwurf=False,
            )
        )
        db.session.commit()
    antwort = einstellungs_client.get("/export/dokumente")
    assert antwort.status_code == 200
    with ZipFile(BytesIO(antwort.data)) as archiv:
        daten = json.loads(archiv.read("metadaten.json"))
        dokument = daten["dokumente"][0]
        assert archiv.read(dokument["archivpfad"]) == inhalt
        assert dokument["sha256"] == hashlib.sha256(inhalt).hexdigest()
    antwort.close()
    assert len(dateien) == 1
    assert dateien[0].closed
