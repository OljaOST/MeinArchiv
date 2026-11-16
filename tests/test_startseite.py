import os
import re
from datetime import date

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.datenbank import Dokument, Kategorie, db

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)


@pytest.fixture
def start_client(monkeypatch):
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


def test_startseite_zaehlt_nur_abgelegte_dokumente(start_client):
    with app.app_context():
        rechnungen = Kategorie(name="Rechnungen")
        db.session.add_all([rechnungen, Kategorie(name="Verträge")])
        db.session.flush()
        db.session.add_all(
            [
                Dokument(
                    dateiname="Rechnung_Firma.pdf",
                    inhalt=b"test",
                    kategorie_id=rechnungen.id,
                    ist_entwurf=False,
                ),
                Dokument(
                    dateiname="ENTWURF_GEHEIM.pdf",
                    inhalt=b"test",
                    kategorie_id=rechnungen.id,
                    ist_entwurf=True,
                ),
                Dokument(
                    dateiname="OhneZuordnung.pdf",
                    inhalt=b"test",
                    ist_entwurf=False,
                ),
            ]
        )
        db.session.commit()

    antwort = start_client.get("/")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert 'id="archiv-anzahl" class="start-anzahl">2 Dokumente' in html
    assert 'class="start-kategorie-anzahl">1 Dokument</span>' in html
    assert 'class="start-kategorie-anzahl">0 Dokumente</span>' in html
    assert "Rechnung_Firma.pdf" in html
    assert "OhneZuordnung.pdf" in html
    assert "Ohne Kategorie" in html
    assert "ENTWURF_GEHEIM.pdf" not in html
    assert 'action="/dokumente"' in html


def test_startseite_zeigt_die_fuenf_zuletzt_abgelegten(start_client):
    with app.app_context():
        # Rückwärts einfügen: das Ablagedatum hat Vorrang vor der ID.
        for tag in range(7, 0, -1):
            db.session.add(
                Dokument(
                    dateiname=f"Beleg_Tag_{tag}.pdf",
                    inhalt=b"test",
                    ablagedatum=date(2026, 1, tag),
                    ist_entwurf=False,
                )
            )
        db.session.commit()

    html = start_client.get("/").get_data(as_text=True)
    namen = [f"Beleg_Tag_{tag}.pdf" for tag in range(7, 2, -1)]
    positionen = [html.index(name) for name in namen]
    assert positionen == sorted(positionen)
    assert "Beleg_Tag_2.pdf" not in html
    assert "Beleg_Tag_1.pdf" not in html


def test_leere_startseite_zeigt_verstaendliche_hinweise(start_client):
    antwort = start_client.get("/")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert "Noch keine Kategorien vorhanden" in html
    assert "Noch keine Dokumente abgelegt" in html
    assert 'href="/scannen"' in html
    assert 'href="/einfuegen"' in html


def test_kategorie_und_suche_bleiben_auf_abgelegte_dokumente_begrenzt(
    start_client,
):
    with app.app_context():
        rechnungen = Kategorie(name="Rechnungen")
        vertraege = Kategorie(name="Verträge")
        db.session.add_all([rechnungen, vertraege])
        db.session.flush()
        kategorie_id = rechnungen.id
        db.session.add_all(
            [
                Dokument(
                    dateiname="Rabatt_10%.pdf",
                    inhalt=b"test",
                    kategorie_id=kategorie_id,
                    ist_entwurf=False,
                ),
                Dokument(
                    dateiname="Normalpreis.pdf",
                    inhalt=b"test",
                    kategorie_id=kategorie_id,
                    ist_entwurf=False,
                ),
                Dokument(
                    dateiname="Fremde_10%.pdf",
                    inhalt=b"test",
                    kategorie_id=vertraege.id,
                    ist_entwurf=False,
                ),
                Dokument(
                    dateiname="Entwurf_10%.pdf",
                    inhalt=b"test",
                    kategorie_id=kategorie_id,
                    ist_entwurf=True,
                ),
            ]
        )
        db.session.commit()

    url = f"/kategorien/{kategorie_id}/dokumente"
    antwort = start_client.get(url)
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert "Rabatt_10%.pdf" in html
    assert "Normalpreis.pdf" in html
    assert "Fremde_10%.pdf" not in html
    assert "Entwurf_10%.pdf" not in html

    # Das Prozentzeichen muss als Text gesucht werden, nicht als SQL-Platzhalter.
    antwort = start_client.get(url, query_string={"q": "%"})
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 200
    assert "Rabatt_10%.pdf" in html
    assert "Normalpreis.pdf" not in html
    assert "Fremde_10%.pdf" not in html
    assert "Entwurf_10%.pdf" not in html


def test_unbekannte_kategorie_liefert_404(start_client):
    assert start_client.get("/kategorien/999999/dokumente").status_code == 404


def test_datenbankfehler_zeigt_keinen_falschen_leerzustand(
    start_client,
    monkeypatch,
):
    def fehlgeschlagene_abfrage(*args, **kwargs):
        raise SQLAlchemyError("Simulierter Datenbankfehler")

    monkeypatch.setattr(db.session, "execute", fehlgeschlagene_abfrage)
    antwort = start_client.get("/")
    html = antwort.get_data(as_text=True)
    assert antwort.status_code == 503
    assert "Übersicht momentan nicht verfügbar" in html
    assert "Noch keine Dokumente abgelegt" not in html


def test_kategorie_datenbankfehler_wird_verstaendlich_angezeigt(
    start_client,
    monkeypatch,
):
    def fehlgeschlagene_abfrage(*args, **kwargs):
        raise SQLAlchemyError("Simulierter Datenbankfehler")

    monkeypatch.setattr(db.session, "get", fehlgeschlagene_abfrage)
    antwort = start_client.get("/kategorien/1/dokumente")
    assert antwort.status_code == 503
    assert "Kategorie momentan nicht verfügbar" in antwort.get_data(as_text=True)


def test_ordner_und_verschieben(start_client):
    with app.app_context():
        quelle = Kategorie(name="Rechnungen")
        ziel = Kategorie(name="Verträge")
        db.session.add_all([quelle, ziel])
        db.session.flush()
        datei = Dokument(
            dateiname="Mein eigener Name.pdf",
            inhalt=b"Originaldatei",
            kategorie_id=quelle.id,
            ist_entwurf=False,
        )
        entwurf = Dokument(
            dateiname="Nicht abgelegt.pdf",
            inhalt=b"Entwurf",
            kategorie_id=quelle.id,
            ist_entwurf=True,
        )
        db.session.add_all([datei, entwurf])
        db.session.commit()
        datei_id, quelle_id, ziel_id = datei.id, quelle.id, ziel.id

    quelle_url = f"/kategorien/{quelle_id}/dokumente"
    ziel_url = f"/kategorien/{ziel_id}/dokumente"
    html = start_client.get("/dokumente").get_data(as_text=True)
    assert f'href="{quelle_url}"' in html
    assert f'href="{ziel_url}"' in html
    assert "Ohne Kategorie" in html
    assert "1 Dokument</span>" in html
    assert "Mein eigener Name.pdf" not in html
    assert "Mein eigener Name.pdf" in start_client.get(
        "/dokumente", query_string={"q": "eigener Name"}
    ).get_data(as_text=True)
    html = start_client.get(quelle_url).get_data(as_text=True)
    assert "Mein eigener Name.pdf" in html
    assert "Nicht abgelegt.pdf" not in html

    verschieben = f"/dokumente/{datei_id}/verschieben"
    html = start_client.get(verschieben).get_data(as_text=True)
    token = re.search(r'name="bestaetigung" value="([^"]+)"', html).group(1)
    assert (
        start_client.post(
            verschieben, data={"bestaetigung": token, "ziel": "999999"}
        ).status_code
        == 400
    )
    antwort = start_client.post(
        verschieben,
        data={"bestaetigung": token, "ziel": str(ziel_id)},
        follow_redirects=True,
    )
    assert antwort.status_code == 200
    assert antwort.request.path == ziel_url
    assert "Dokument verschoben." in antwort.get_data(as_text=True)
    assert "Mein eigener Name.pdf" in antwort.get_data(as_text=True)
    assert "Mein eigener Name.pdf" not in start_client.get(quelle_url).get_data(
        as_text=True
    )
    assert (
        start_client.post(
            verschieben, data={"bestaetigung": token, "ziel": ""}
        ).status_code
        == 409
    )

    html = start_client.get(verschieben).get_data(as_text=True)
    token = re.search(r'name="bestaetigung" value="([^"]+)"', html).group(1)
    antwort = start_client.post(
        verschieben, data={"bestaetigung": token, "ziel": ""}, follow_redirects=True
    )
    assert antwort.request.path == "/dokumente/ohne-kategorie"
    assert "Mein eigener Name.pdf" in antwort.get_data(as_text=True)
    with app.app_context():
        dokument = db.session.get(Dokument, datei_id)
        assert dokument.kategorie_id is None
        assert dokument.dateiname == "Mein eigener Name.pdf"
        assert dokument.inhalt == b"Originaldatei"
        assert dokument.ablagedatum is None


def test_ordner_dateiliste_umbenennen_und_loeschen(start_client):
    with app.app_context():
        ordner = Kategorie(name="Rechnungen")
        db.session.add(ordner)
        db.session.flush()
        datei = Dokument(
            dateiname="Original.pdf",
            inhalt=b"Dateiinhalt",
            kategorie_id=ordner.id,
            ist_entwurf=False,
        )
        db.session.add(datei)
        db.session.commit()
        datei_id, ordner_id = datei.id, ordner.id

    ordner_url = f"/kategorien/{ordner_id}/dokumente"
    basis = f"/dokumente/{datei_id}"
    html = start_client.get(ordner_url).get_data(as_text=True)
    assert f'href="{basis}">Original.pdf</a>' in html
    assert '<input type="search"' not in html
    assert "Umbenennen</a>" in html
    assert "Verschieben</a>" in html
    assert "Löschen</a>" in html

    url = basis + "/umbenennen"
    html = start_client.get(url).get_data(as_text=True)
    token = re.search(r'name="bestaetigung" value="([^"]+)"', html).group(1)
    assert (
        start_client.post(
            url, data={"bestaetigung": token, "dateiname": "../Ungültig"}
        ).status_code
        == 400
    )
    antwort = start_client.post(
        url,
        data={"bestaetigung": token, "dateiname": "Mein Beleg.pdf"},
        follow_redirects=True,
    )
    assert antwort.request.path == ordner_url
    assert "Mein Beleg.pdf" in antwort.get_data(as_text=True)
    with app.app_context():
        dokument = db.session.get(Dokument, datei_id)
        assert dokument.dateiname == "Mein Beleg.pdf"
        assert dokument.kategorie_id == ordner_id
        assert dokument.inhalt == b"Dateiinhalt"

    url = basis + "/loeschen?aus_ordner=1"
    html = start_client.get(url).get_data(as_text=True)
    token = re.search(r'name="bestaetigung" value="([^"]+)"', html).group(1)
    antwort = start_client.post(
        url, data={"bestaetigung": token, "loeschen": "ja"}, follow_redirects=True
    )
    assert antwort.request.path == ordner_url
    assert "In diesem Ordner sind noch keine Dokumente abgelegt." in antwort.get_data(
        as_text=True
    )
