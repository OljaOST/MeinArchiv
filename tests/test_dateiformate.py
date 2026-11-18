import zipfile
from io import BytesIO

import pytest

from app.dateiformate import (
    DATEIFORMATE,
    ERLAUBTE_ENDUNGEN,
    inhalt_passt_zur_endung,
)

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
DOC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 16
PROGRAMM = b"MZ\x90\x00\x03\x00\x00\x00"


def zip_mit(*dateinamen):
    puffer = BytesIO()
    with zipfile.ZipFile(puffer, "w") as archiv:
        for name in dateinamen:
            archiv.writestr(name, "<xml/>")
    return puffer.getvalue()


DOCX = zip_mit("[Content_Types].xml", "word/document.xml")


def test_erlaubte_endungen_entsprechen_der_formatliste():
    assert ERLAUBTE_ENDUNGEN == {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    assert set(DATEIFORMATE) == ERLAUBTE_ENDUNGEN


@pytest.mark.parametrize(
    ("inhalt", "endung"),
    [
        (PDF, ".pdf"),
        (PNG, ".png"),
        (JPEG, ".jpg"),
        (JPEG, ".jpeg"),
        (DOC, ".doc"),
        (DOCX, ".docx"),
    ],
)
def test_echte_dateien_werden_angenommen(inhalt, endung):
    assert inhalt_passt_zur_endung(inhalt, endung)


def test_endung_in_grossbuchstaben_wird_angenommen():
    assert inhalt_passt_zur_endung(PDF, ".PDF")


@pytest.mark.parametrize(
    ("inhalt", "endung"),
    [
        (PROGRAMM, ".pdf"),
        (PNG, ".pdf"),
        (PDF, ".png"),
        (JPEG, ".png"),
        (PDF, ".docx"),
        (b"Nur ein Text", ".jpg"),
    ],
)
def test_umbenannte_dateien_werden_abgewiesen(inhalt, endung):
    assert not inhalt_passt_zur_endung(inhalt, endung)


def test_leere_datei_wird_abgewiesen():
    assert not inhalt_passt_zur_endung(b"", ".pdf")


def test_nicht_erlaubte_endung_wird_abgewiesen():
    assert not inhalt_passt_zur_endung(PROGRAMM, ".exe")


def test_pdf_mit_vorangestellten_bytes_wird_angenommen():
    # Die PDF-Spezifikation erlaubt Bytes vor der Kennung %PDF-.
    assert inhalt_passt_zur_endung(b"\x00\x00Kopf" + PDF, ".pdf")


def test_pdf_kennung_innerhalb_der_ersten_1024_bytes_wird_angenommen():
    assert inhalt_passt_zur_endung(b"x" * 1023 + PDF, ".pdf")


def test_pdf_kennung_nach_1024_bytes_wird_abgewiesen():
    assert not inhalt_passt_zur_endung(b"x" * 1024 + PDF, ".pdf")


def test_beliebiges_zip_als_docx_wird_abgewiesen():
    assert not inhalt_passt_zur_endung(zip_mit("bild.png"), ".docx")


def test_beschaedigtes_zip_als_docx_wird_abgewiesen():
    assert not inhalt_passt_zur_endung(b"PK\x03\x04kaputt", ".docx")
