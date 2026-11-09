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