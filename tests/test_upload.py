from io import BytesIO

import pytest

from app import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app.config, "TESTING", True)

    with app.test_client() as test_client:
        yield test_client


def test_upload_ohne_datei_wird_abgewiesen(client):
    antwort = client.post("/dokumente/vorbereiten")

    assert antwort.status_code == 400
    assert antwort.get_json()["fehler"] == "Bitte eine Datei auswählen."


def test_upload_mit_unerlaubtem_format_wird_abgewiesen(client):
    antwort = client.post(
        "/dokumente/vorbereiten",
        data={
            "dokument": (BytesIO(b"Testinhalt"), "programm.exe"),
        },
    )

    assert antwort.status_code == 400
    assert antwort.get_json()["fehler"] == (
        "Dieses Dateiformat wird nicht unterstützt."
    )


def test_upload_mit_leerer_datei_wird_abgewiesen(client):
    antwort = client.post(
        "/dokumente/vorbereiten",
        data={
            "dokument": (BytesIO(b""), "rechnung.pdf"),
        },
    )

    assert antwort.status_code == 400
    assert antwort.get_json()["fehler"] == "Die Datei ist leer."


@pytest.mark.parametrize("quelle", ["hochladen", "einfuegen", None])
def test_umbenanntes_programm_wird_abgewiesen(client, monkeypatch, quelle):
    # Ein Programm, das in rechnung.pdf umbenannt wurde, darf weder gespeichert
    # noch an OpenAI gesendet werden.
    monkeypatch.setattr(
        "app.namensvorschlag_vorbereiten",
        lambda *args: pytest.fail("Die Datei wurde an OpenAI weitergegeben."),
    )
    daten = {"dokument": (BytesIO(b"MZ\x90\x00Programm"), "rechnung.pdf")}
    if quelle:
        daten["quelle"] = quelle

    antwort = client.post("/dokumente/vorbereiten", data=daten)

    assert antwort.status_code == 400
    assert antwort.get_json()["fehler"] == (
        "Der Dateiinhalt passt nicht zum Format .pdf."
    )


def test_scan_ohne_pdf_inhalt_wird_abgewiesen(client):
    antwort = client.post(
        "/dokumente/vorbereiten",
        data={
            "dokument": (BytesIO(b"\x89PNG\r\n\x1a\nBild"), "scan.pdf"),
            "quelle": "scan",
        },
    )

    assert antwort.status_code == 400
    assert antwort.get_json()["fehler"] == "Das Scan-PDF konnte nicht gelesen werden."
