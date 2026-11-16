# Gemeinsame Speichervorschau für neue Dokumente

Date: 2026-11-11

## Status

Accepted

## Context

Scannen, Hochladen und Einfügen sollen nach dem Übernehmen der Datei eine Vorschau mit dem Dokumentnamen und der Speicheraktion zeigen. Die zusätzliche KI-Abfrage und das Formular für Firma und Kategorie entfallen für neue Dokumente.

## Options considered

* Die Datei nach der Erkennung sofort archivieren. Damit entfällt die Möglichkeit, den Namen vor der Ablage zu prüfen.
* Die Datei als Entwurf vorbereiten und den vorgeschlagenen Namen in der Vorschau bestätigen lassen. Damit lassen sich die Vorschau und die Speicheraktion aus der Vorlage umsetzen.

## Decision

Alle drei Eingänge nutzen die Speichervorschau für einen Entwurf. Der Upload weist vor dem Absenden auf die Übermittlung an OpenAI hin. Der Server verwendet die bestehende Erkennung und die bestehende Regel für Dateinamen. Er speichert erkannte Firma und Kategorie im Hintergrund und zeigt den bearbeitbaren Dateinamen an. Die Speicheraktion übernimmt den Entwurf ins Archiv.

## Reasons

Die Nutzerin kann die Datei und den Namen vor der Ablage prüfen. Alle Eingänge verwenden dieselben Regeln und denselben Speicherweg.

## Consequences

Wenn kein KI-Ergebnis verfügbar ist, erscheint der bisherige Dateiname als Ausgangspunkt. Das Öffnen der Vorschau oder eines alten Entwurfs löst keine Übermittlung aus. Die manuelle KI-Analyse eines bereits abgelegten Dokuments bleibt als eigene Aktion verfügbar. Für diese Änderung ist keine Datenbankmigration nötig.
