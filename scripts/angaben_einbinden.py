"""Die vorhandene Kategorie-Route gezielt mit der Angabenbearbeitung verbinden."""

import ast
import os
import shutil
import tempfile
from pathlib import Path

IMPORT = "from .dokumentbearbeitung import dokument_angaben_bearbeiten\n"
FUNKTION = (
    "def dokument_kategorie(dokument_id):\n"
    "    return dokument_angaben_bearbeiten(dokument_id)\n"
)


def einbinden(projekt):
    projekt = Path(projekt).resolve()
    ziel = projekt / "src/app/__init__.py"
    helfer = projekt / "src/app/dokumentbearbeitung.py"
    if not (projekt / "pyproject.toml").is_file() or not helfer.is_file():
        raise ValueError(
            "Bitte zuerst die neuen Dateien ins MeinArchiv-Projekt kopieren "
            "und das Skript dort im Ordner scripts ausführen."
        )
    vorher = ziel.read_text(encoding="utf-8")
    baum = ast.parse(vorher)
    funktionen = [
        knoten
        for knoten in baum.body
        if isinstance(knoten, ast.FunctionDef) and knoten.name == "dokument_kategorie"
    ]
    if len(funktionen) != 1:
        raise ValueError(
            "Die Funktion dokument_kategorie wurde nicht eindeutig gefunden."
        )
    funktion = funktionen[0]
    passende_route = any(
        isinstance(dekorator, ast.Call)
        and isinstance(dekorator.func, ast.Attribute)
        and dekorator.func.attr == "route"
        and dekorator.args
        and isinstance(dekorator.args[0], ast.Constant)
        and dekorator.args[0].value == "/dokumente/<int:dokument_id>/kategorie"
        for dekorator in funktion.decorator_list
    )
    if not passende_route:
        raise ValueError(
            "Die erwartete Kategorie-Route fehlt. Es wurde nichts geändert."
        )

    zeilen = vorher.splitlines(keepends=True)
    nachher = "".join(
        zeilen[: funktion.lineno - 1] + [FUNKTION] + zeilen[funktion.end_lineno :]
    )
    import_vorhanden = any(
        isinstance(knoten, ast.ImportFrom)
        and knoten.level == 1
        and knoten.module == "dokumentbearbeitung"
        and any(
            name.name == "dokument_angaben_bearbeiten" and name.asname is None
            for name in knoten.names
        )
        for knoten in baum.body
    )
    if not import_vorhanden:
        # Modul-Dokumentation und eventuelle __future__-Imports bleiben vorne.
        position = 0
        for i, knoten in enumerate(baum.body):
            if (
                i == 0
                and isinstance(knoten, ast.Expr)
                and isinstance(knoten.value, ast.Constant)
                and isinstance(knoten.value.value, str)
            ):
                position = knoten.end_lineno
            elif isinstance(knoten, ast.ImportFrom) and knoten.module == "__future__":
                position = knoten.end_lineno
            else:
                break
        neue_zeilen = nachher.splitlines(keepends=True)
        neue_zeilen.insert(position, IMPORT)
        nachher = "".join(neue_zeilen)

    compile(nachher, str(ziel), "exec")
    if nachher == vorher:
        return None

    sicherung = Path(tempfile.mkdtemp(prefix="meinarchiv-angaben-")) / "__init__.py"
    shutil.copy2(ziel, sicherung)
    datei_nr, temp_name = tempfile.mkstemp(
        prefix=".angaben-", suffix=".tmp", dir=ziel.parent
    )
    try:
        with os.fdopen(datei_nr, "w", encoding="utf-8") as datei:
            datei.write(nachher)
        shutil.copymode(ziel, temp_name)
        os.replace(temp_name, ziel)
    finally:
        if Path(temp_name).exists():
            Path(temp_name).unlink()
    return sicherung


def main():
    projekt = Path(__file__).resolve().parents[1]
    try:
        sicherung = einbinden(projekt)
    except (OSError, ValueError, SyntaxError) as fehler:
        raise SystemExit(f"Einbindung nicht abgeschlossen: {fehler}") from None
    if sicherung is None:
        print("Die Angabenbearbeitung ist bereits eingebunden.")
    else:
        print("Kategorie-Route mit der Angabenbearbeitung verbunden.")
        print(f"Sicherung der bisherigen __init__.py: {sicherung}")
    print(
        "Alle anderen Routen bleiben erhalten. Es wurden keine Dokumentdaten geändert."
    )


if __name__ == "__main__":
    main()
