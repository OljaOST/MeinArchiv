import runpy
from pathlib import Path

import pytest


def _projekt(tmp_path, route="/dokumente/<int:dokument_id>/kategorie"):
    ordner = tmp_path / "src/app"
    ordner.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
    (ordner / "dokumentbearbeitung.py").write_text("# Testhelfer\n")
    (ordner / "__init__.py").write_text(
        "from __future__ import annotations\n\n"
        f'@app.route("{route}", methods=["GET", "POST"])\n'
        "def dokument_kategorie(dokument_id):\n"
        '    return "bisherige Bearbeitung"\n\n'
        '@app.route("/andere-route")\n'
        "def andere_route():\n"
        '    return "unveraendert"\n'
    )
    return ordner / "__init__.py"


def _einbinden():
    skript = Path(__file__).resolve().parents[1] / "scripts/angaben_einbinden.py"
    return runpy.run_path(str(skript))["einbinden"]


def test_einbindung_erhaelt_andere_routen_und_sichert_original(tmp_path):
    ziel = _projekt(tmp_path)
    vorher = ziel.read_text()
    sicherung = _einbinden()(tmp_path)
    nachher = ziel.read_text()
    assert sicherung.read_text() == vorher
    assert "return dokument_angaben_bearbeiten(dokument_id)" in nachher
    assert (
        '@app.route("/andere-route")\ndef andere_route():\n    return "unveraendert"'
        in nachher
    )
    assert nachher.startswith("from __future__ import annotations\n")
    compile(nachher, str(ziel), "exec")


def test_einbindung_ist_wiederholbar(tmp_path):
    ziel = _projekt(tmp_path)
    einbinden = _einbinden()
    einbinden(tmp_path)
    nachher = ziel.read_text()
    assert einbinden(tmp_path) is None
    assert ziel.read_text() == nachher


def test_unerwartete_route_wird_nicht_veraendert(tmp_path):
    ziel = _projekt(tmp_path, route="/andere-kategorie-route")
    vorher = ziel.read_text()
    with pytest.raises(ValueError, match="erwartete Kategorie-Route"):
        _einbinden()(tmp_path)
    assert ziel.read_text() == vorher
