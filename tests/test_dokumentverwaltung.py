import os
import re
from datetime import date

import pytest
from itsdangerous import SignatureExpired
from sqlalchemy.exc import SQLAlchemyError

from app import app, dokumentansicht
from app.datenbank import Dokument, Kategorie, db

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)


@pytest.fixture
def verwaltungs_client(monkeypatch):
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


def _speichere_dokument(**werte):
    daten = dict(dateiname="Beleg.pdf", inhalt=b"Testinhalt", ist_entwurf=False)
    daten.update(werte)
    with app.app_context():
        dokument = Dokument(**daten)
        db.session.add(dokument)
        db.session.commit()
        return dokument.id


def _lese_bestaetigung(client, dokument_id):
    antwort = client.get(f"/dokumente/{dokument_id}/loeschen")
    assert antwort.status_code == 200
    treffer = re.search(
        r'name="bestaetigung" value="([^"]+)"',
        antwort.get_data(as_text=True),
    )
    assert treffer is not None
    return treffer.group(1)


def test_detailansicht_zeigt_angaben_und_aktionen(verwaltungs_client):
    dokument_id = _speichere_dokument(
        dateiname="261109_Rechnung_Muster.pdf",
        firma="Muster GmbH",
        ablagedatum=date(2026, 11, 9),
    )
    antwort = verwaltungs_client.get(f"/dokumente/{dokument_id}")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert "261109_Rechnung_Muster.pdf" in html
    assert "Muster GmbH" in html
    assert "09.11.2026" in html
    assert "Ohne Kategorie" in html
    assert f"/dokumente/{dokument_id}/download" in html
    assert f"/dokumente/{dokument_id}/vorschau" in html
    assert f"/dokumente/{dokument_id}/loeschen" in html


def test_aeltere_dokumente_ohne_metadaten_bleiben_anzeigbar(verwaltungs_client):
    dokument_id = _speichere_dokument()
    antwort = verwaltungs_client.get(f"/dokumente/{dokument_id}")
    assert antwort.status_code == 200
    assert "Nicht hinterlegt" in antwort.get_data(as_text=True)


@pytest.mark.parametrize(
    "endung, mimetype",
    [
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".pdf", "application/pdf"),
    ],
)
def test_vorschau_uebertraegt_dateibytes_inline(
    verwaltungs_client,
    endung,
    mimetype,
):
    inhalt = b"Unveraenderte gespeicherte Dateibytes"
    dokument_id = _speichere_dokument(dateiname=f"Beleg{endung}", inhalt=inhalt)
    antwort = verwaltungs_client.get(f"/dokumente/{dokument_id}/vorschau")
    assert antwort.status_code == 200
    assert antwort.mimetype == mimetype
    assert antwort.data == inhalt
    assert antwort.headers["Content-Disposition"].startswith("inline;")
    assert antwort.headers["X-Content-Type-Options"] == "nosniff"
    assert antwort.headers["Cache-Control"] == "no-store"
    antwort.close()


def test_word_hat_download_statt_browservorschau(verwaltungs_client):
    dokument_id = _speichere_dokument(dateiname="Beleg.docx")
    antwort = verwaltungs_client.get(f"/dokumente/{dokument_id}")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert "keine Vorschau" in html
    assert "<iframe" not in html
    assert (
        verwaltungs_client.get(f"/dokumente/{dokument_id}/vorschau").status_code == 415
    )


@pytest.mark.parametrize("suffix", ["", "/vorschau", "/loeschen"])
def test_unbekannte_dokumente_liefern_404(verwaltungs_client, suffix):
    assert verwaltungs_client.get(f"/dokumente/999999{suffix}").status_code == 404


@pytest.mark.parametrize("suffix", ["", "/vorschau", "/loeschen"])
def test_neue_ansichten_zeigen_keine_entwuerfe(verwaltungs_client, suffix):
    dokument_id = _speichere_dokument(ist_entwurf=True)
    assert (
        verwaltungs_client.get(f"/dokumente/{dokument_id}{suffix}").status_code == 404
    )


def test_oeffnen_der_loeschseite_loescht_nichts(verwaltungs_client):
    dokument_id = _speichere_dokument()
    _lese_bestaetigung(verwaltungs_client, dokument_id)
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None


@pytest.mark.parametrize("token", ["", "manipuliert"])
def test_loeschen_braucht_gueltige_bestaetigung(verwaltungs_client, token):
    dokument_id = _speichere_dokument()
    antwort = verwaltungs_client.post(
        f"/dokumente/{dokument_id}/loeschen",
        data={"loeschen": "ja", "bestaetigung": token},
    )
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None


def test_loeschen_braucht_auch_die_checkbox(verwaltungs_client):
    dokument_id = _speichere_dokument()
    token = _lese_bestaetigung(verwaltungs_client, dokument_id)
    antwort = verwaltungs_client.post(
        f"/dokumente/{dokument_id}/loeschen",
        data={"bestaetigung": token},
    )
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None


def test_bestaetigung_gilt_nur_fuer_das_gewaehlte_dokument(verwaltungs_client):
    erstes = _speichere_dokument(dateiname="Erstes.pdf")
    zweites = _speichere_dokument(dateiname="Zweites.pdf")
    token = _lese_bestaetigung(verwaltungs_client, erstes)
    antwort = verwaltungs_client.post(
        f"/dokumente/{zweites}/loeschen",
        data={"bestaetigung": token, "loeschen": "ja"},
    )
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, erstes) is not None
        assert db.session.get(Dokument, zweites) is not None


def test_abgelaufene_bestaetigung_loescht_nichts(verwaltungs_client, monkeypatch):
    dokument_id = _speichere_dokument()
    token = _lese_bestaetigung(verwaltungs_client, dokument_id)

    def abgelaufen(*args, **kwargs):
        raise SignatureExpired("Abgelaufen")

    monkeypatch.setattr(dokumentansicht._loesch_bestaetigung, "loads", abgelaufen)
    antwort = verwaltungs_client.post(
        f"/dokumente/{dokument_id}/loeschen",
        data={"bestaetigung": token, "loeschen": "ja"},
    )
    assert antwort.status_code == 400
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None


def test_loeschen_entfernt_nur_das_gewaehlte_dokument(verwaltungs_client):
    with app.app_context():
        kategorie = Kategorie(name="Rechnung")
        db.session.add(kategorie)
        db.session.commit()
        kategorie_id = kategorie.id
    erstes = _speichere_dokument(kategorie_id=kategorie_id)
    zweites = _speichere_dokument(dateiname="Bleibt.pdf", kategorie_id=kategorie_id)
    token = _lese_bestaetigung(verwaltungs_client, erstes)
    antwort = verwaltungs_client.post(
        f"/dokumente/{erstes}/loeschen",
        data={"bestaetigung": token, "loeschen": "ja"},
    )
    assert antwort.status_code == 303
    assert antwort.headers["Location"].endswith("/dokumente")
    with app.app_context():
        assert db.session.get(Dokument, erstes) is None
        assert db.session.get(Dokument, zweites) is not None
        assert db.session.get(Kategorie, kategorie_id) is not None
    assert verwaltungs_client.get(f"/dokumente/{erstes}").status_code == 404
    assert (
        verwaltungs_client.post(
            f"/dokumente/{erstes}/loeschen",
            data={"bestaetigung": token, "loeschen": "ja"},
        ).status_code
        == 404
    )


def test_fehlgeschlagener_commit_rollt_loeschung_zurueck(
    verwaltungs_client,
    monkeypatch,
):
    dokument_id = _speichere_dokument()
    token = _lese_bestaetigung(verwaltungs_client, dokument_id)

    def fehlgeschlagener_commit():
        raise SQLAlchemyError("Simulierter Commitfehler")

    with monkeypatch.context() as aenderungen:
        aenderungen.setattr(db.session, "commit", fehlgeschlagener_commit)
        antwort = verwaltungs_client.post(
            f"/dokumente/{dokument_id}/loeschen",
            data={"bestaetigung": token, "loeschen": "ja"},
        )
    assert antwort.status_code == 503
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None


def test_nachtraeglich_als_entwurf_markiertes_dokument_wird_nicht_geloescht(
    verwaltungs_client,
):
    dokument_id = _speichere_dokument()
    token = _lese_bestaetigung(verwaltungs_client, dokument_id)
    with app.app_context():
        db.session.get(Dokument, dokument_id).ist_entwurf = True
        db.session.commit()
    antwort = verwaltungs_client.post(
        f"/dokumente/{dokument_id}/loeschen",
        data={"bestaetigung": token, "loeschen": "ja"},
    )
    assert antwort.status_code == 404
    with app.app_context():
        assert db.session.get(Dokument, dokument_id) is not None
