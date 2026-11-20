# Codeprüfung mit ruff und black in der Pipeline

Date: 2026-11-20

## Status

Proposed

## Context

Das Projekt-Template der Dozierenden richtet in `pyproject.toml` zwei Werkzeuge ein:
black formatiert den Code, ruff prüft ihn auf Fehler und unsortierte Importe (Regeln E, F, I, B).
VS Code formatiert beim Speichern mit black. Die GitHub-Actions-Pipeline aus Entscheidung 0001
führte bisher aber nur pytest aus. Dadurch war der Code nicht einheitlich: black hätte 7 Dateien
umformatiert, ruff fand unsortierte Importe in `src/app/__init__.py`.

## Options Considered

- Nichts ändern: Formatierung bleibt freiwillig und hängt vom Editor ab.
- Auf ruff als einziges Werkzeug umstellen (`ruff format` statt black): ein Werkzeug weniger,
  weicht aber von der Vorgabe des Templates ab.
- Die Template-Einstellungen beibehalten und in der Pipeline durchsetzen: `ruff check` und
  `black --check` laufen vor den Tests.

## Decision

Wir behalten black und ruff wie im Template vorgesehen und prüfen beides in der Pipeline vor
pytest. Der Code wurde einmalig mit black formatiert und die Importe mit ruff sortiert.
Geprüft werden `src`, `tests` und `scripts`. Die von Alembic erzeugten Migrationen in
`migrations/` sind ausgenommen.

## Reasons

Die Einstellungen der Dozierenden bleiben unverändert; die Pipeline setzt nur durch, was das
Template bereits vorgibt. Abweichungen fallen im Pull Request auf und nicht erst beim Review.
Die Migrationen werden von Alembic generiert und nachträglich nicht von Hand bearbeitet.

## Consequences

- Ein Pull Request wird rot, wenn Code nicht black-formatiert ist oder ruff-Regeln verletzt.
- Vor einem Push lokal ausführen: `uv run black src tests scripts` und
  `uv run ruff check --fix src tests scripts`.
- Die einmalige Formatierung ändert nur die Darstellung, nicht die Logik. Offene Branches
  sollten danach auf den neuen Stand von master gebracht werden.
- Die Prüfung läuft im bestehenden Job `tests`. Ein Branch-Schutz mit Status-Check `tests`
  deckt damit auch Lint und Formatierung ab.
