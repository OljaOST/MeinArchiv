import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import ki


@pytest.fixture
def openai_client(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client

    client.responses.create.return_value = SimpleNamespace(
        status="completed",
        output_text='{"kategorie": "Rechnung", "firma": "Muster GmbH"}',
    )

    monkeypatch.setattr(
        ki,
        "OpenAI",
        MagicMock(return_value=client),
    )

    return client


def test_pdf_wird_uebergeben_und_ergebnis_gelesen(openai_client):
    inhalt = b"PDF-Testinhalt"

    ergebnis = ki.erkenne_dokument(
        inhalt,
        ".pdf",
        ["Rechnung", "Vertrag"],
    )

    assert ergebnis == {
        "kategorie": "Rechnung",
        "firma": "Muster GmbH",
    }

    openai_client.responses.create.assert_called_once()

    anfrage = openai_client.responses.create.call_args.kwargs
    dateieingabe = anfrage["input"][0]["content"][0]

    assert dateieingabe["type"] == "input_file"
    assert dateieingabe["file_data"].startswith("data:application/pdf;base64,")

    kodierter_inhalt = dateieingabe["file_data"].split(",", 1)[1]
    assert base64.b64decode(kodierter_inhalt) == inhalt

    schema = anfrage["text"]["format"]["schema"]
    assert schema["properties"]["kategorie"]["enum"] == [
        None,
        "Rechnung",
        "Vertrag",
    ]

    assert anfrage["store"] is False


def test_png_wird_als_bild_uebergeben(openai_client):
    inhalt = b"Bild-Testinhalt"

    ki.erkenne_dokument(inhalt, ".png", ["Rechnung"])

    anfrage = openai_client.responses.create.call_args.kwargs
    dateieingabe = anfrage["input"][0]["content"][0]

    assert dateieingabe["type"] == "input_image"
    assert dateieingabe["image_url"].startswith("data:image/png;base64,")

    kodierter_inhalt = dateieingabe["image_url"].split(",", 1)[1]
    assert base64.b64decode(kodierter_inhalt) == inhalt


def test_unvollstaendige_antwort_wird_abgewiesen(openai_client):
    openai_client.responses.create.return_value.status = "incomplete"

    with pytest.raises(ValueError, match="vollständiges Ergebnis"):
        ki.erkenne_dokument(
            b"PDF-Testinhalt",
            ".pdf",
            ["Rechnung"],
        )


def test_unerlaubtes_format_wird_vor_der_anfrage_abgewiesen(openai_client):
    with pytest.raises(ValueError, match="Dateiformat"):
        ki.erkenne_dokument(
            b"Testinhalt",
            ".exe",
            ["Rechnung"],
        )

    openai_client.responses.create.assert_not_called()