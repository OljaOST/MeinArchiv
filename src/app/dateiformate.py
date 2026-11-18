"""Erlaubte Dateiformate und Prüfung des tatsächlichen Dateiinhalts.

Die Dateiendung ist nur ein Teil des Dateinamens und wird vom Browser
mitgeschickt. Sie sagt nichts darüber aus, was die Datei wirklich enthält.
Dieses Modul prüft deshalb zusätzlich die Dateisignatur: Fast jedes Format
beginnt mit festen Erkennungsbytes.

Die Prüfung ist kein Virenscanner. Sie stellt nur sicher, dass eine Datei dem
Format entspricht, das ihre Endung angibt.
"""

import zipfile
from io import BytesIO

# Zentrale Liste der erlaubten Formate mit ihrem Dateityp (MIME-Typ).
DATEIFORMATE = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".doc": "application/msword",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}

ERLAUBTE_ENDUNGEN = frozenset(DATEIFORMATE)

# Erkennungsbytes am Dateianfang.
_SIGNATUREN = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
    # Altes Word-Format (OLE). Dieselbe Signatur haben auch alte Excel- und
    # PowerPoint-Dateien. Diese Grenze ist bekannt und akzeptiert.
    ".doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    # DOCX ist intern ein ZIP-Archiv.
    ".docx": b"PK\x03\x04",
}

# Laut PDF-Spezifikation darf die Kennung %PDF- irgendwo in den ersten
# 1024 Bytes stehen. PDF-Reader akzeptieren solche Dateien ebenfalls.
_PDF_KENNUNG = b"%PDF-"
_PDF_SUCHBEREICH = 1024


def _ist_word_dokument(inhalt):
    # Jedes ZIP beginnt mit PK. Ein Word-Dokument enthält zusätzlich
    # word/document.xml. namelist() liest nur das Inhaltsverzeichnis des
    # Archivs und entpackt nichts.
    try:
        with zipfile.ZipFile(BytesIO(inhalt)) as archiv:
            return "word/document.xml" in archiv.namelist()
    except zipfile.BadZipFile:
        return False


def inhalt_passt_zur_endung(inhalt, endung):
    """Prüft, ob der Dateiinhalt zum Format der Endung passt."""
    endung = endung.lower()

    if endung not in ERLAUBTE_ENDUNGEN or not inhalt:
        return False

    if endung == ".pdf":
        anfang = inhalt[: _PDF_SUCHBEREICH + len(_PDF_KENNUNG)]
        position = anfang.find(_PDF_KENNUNG)
        return 0 <= position < _PDF_SUCHBEREICH

    if not inhalt.startswith(_SIGNATUREN[endung]):
        return False

    if endung == ".docx":
        return _ist_word_dokument(inhalt)

    return True
