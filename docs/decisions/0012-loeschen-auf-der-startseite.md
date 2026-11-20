# Löschen auch unter «Zuletzt abgelegt» auf der Startseite

Date: 2026-11-20

## Status

Proposed

## Context

Entscheidung 0005 führt das Löschen über eine eigene Bestätigungsseite ein. Erreichbar war sie
über die Detailseite und die Dateiliste eines Ordners. Auf der Startseite zeigt «Zuletzt
abgelegt» nur «Öffnen» und «Herunterladen». Fehlscans fallen aber meist genau dort auf,
direkt nach dem Speichern. Beim Testen war nicht ersichtlich, dass man zum Löschen zuerst ein
Dokument öffnen muss.

## Options Considered

- Nichts ändern: Löschen bleibt eine Ebene tiefer. Schützt vor Fehlklicks, ist aber schwer zu
  finden.
- Ein «X» oben rechts im Eintrag: kompakt, wirkt aber wie «aus der Liste ausblenden» statt
  «endgültig löschen».
- Ein Link «Löschen» neben «Öffnen» und «Herunterladen», der auf die bestehende
  Bestätigungsseite führt.

## Decision

Wir ergänzen in «Zuletzt abgelegt» einen Link «Löschen» in der Warnfarbe der Detailseite. Er
führt mit dem Parameter `von=start` auf die bestehende Bestätigungsseite. «Abbrechen» und die
Weiterleitung nach dem Löschen führen zurück zur Startseite.

## Reasons

Die Löschlogik aus 0005 bleibt unverändert: Bestätigungsseite, signierter Code, POST. Der
Schutz vor versehentlichem Löschen ist damit derselbe wie bisher, nur der Einstieg ist
einfacher zu finden. Der Parameter folgt dem bestehenden Muster `aus_ordner=1`.

## Consequences

- Löschen ist an drei Stellen erreichbar: Startseite, Ordner und Detailseite.
- Die Bestätigungsseite zeigt den passenden Rücklink («Zurück zur Startseite», «Zurück zum
  Ordner» oder «Zurück zum Dokument»).
- Ohne Anmeldung kann weiterhin jede Person mit Zugriff auf die öffentliche URL Dokumente
  löschen. Das war schon vor dieser Änderung so und bleibt ein bekanntes Risiko, bis eine
  Anmeldung eingeführt wird.
