# Automatische Tests mit GitHub Actions

Date: 2026-11-09

## Status

Accepted

## Context

Die vorhandenen Tests sollen nach Änderungen automatisch ausgeführt werden.

## Options Considered

- Tests manuell auf dem eigenen Computer ausführen.
- Tests zusätzlich bei jedem Push mit GitHub Actions ausführen.

## Decision

Wir ergänzen einen GitHub-Actions-Workflow für pytest.

## Reasons

GitHub wird bereits für die Versionsverwaltung verwendet.
Die Pipeline nutzt wie die lokale Entwicklung Python und uv.

## Consequences

Testergebnisse werden auf GitHub sichtbar.
Die bisherigen KI-Tests verwenden simulierte Antworten.
Datenbankintegration und Deployment werden später ergänzt.