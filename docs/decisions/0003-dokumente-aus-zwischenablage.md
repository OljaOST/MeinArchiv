# Dokumente aus der Zwischenablage übernehmen

Date: 2026-11-09

## Status

Accepted

## Context

Die Vorlage von MeinArchiv enthält die Aktion Einfügen. Gemäss der Klarstellung der Entwicklerin sollen Dokumente übernommen werden, kein eingegebener Text. Uploadentwürfe, KI-Freigabe und Bestätigung erkannter Angaben sind bereits vorhanden.

## Options Considered

* Browser-Zwischenablage über Paste-Ereignis und Clipboard.read(): keine Zusatzbibliothek, aber vom Browser und der kopierenden Anwendung abhängig.
* Native Desktop-App: mehr Zugriff auf die Betriebssystem-Zwischenablage, aber zusätzlicher Technologiestack ausserhalb der bestehenden Webanwendung.
* Nur Dateiupload: zuverlässig verfügbar, bildet den gewünschten Einfügen-Ablauf alleine jedoch nicht ab.

## Decision

Die bestehende Webanwendung erhält eine separate Einfügen-Seite. Sie verarbeitet echte Dateiobjekte aus dem Paste-Ereignis oder nach ausdrücklichem Klick über Clipboard.read(). Die vorhandene Dateiauswahl bleibt als Alternative. Der bestehende Flask-Upload-Endpunkt verarbeitet die gewählte Datei unverändert weiter.

## Reasons

Die Erweiterung passt zum vorhandenen Flask-/JavaScript-Aufbau und zum Wunsch nach grösseren zusammenhängenden Umsetzungsschritten. Vor dem ausdrücklichen Übernehmen erfolgt kein Upload. Die OpenAI-Freigabe bleibt eine separate Aktion.

## Consequences

* Reiner Text, Links und Dateipfade werden nicht zu Dokumenten umgewandelt.
* Ein Dokument wird pro Vorgang übernommen. Mehrere eingefügte Dateien werden mit einer Erklärung abgewiesen.
* Die Clipboard-API wird nur nach Klick gelesen. Das Paste-Ereignis verarbeitet die durch die Nutzerin eingefügten Daten.
* Unterstützte Clipboard-Formate und Berechtigungen hängen vom Browser ab. Kopieren einer Datei im Finder garantiert keine im Browser lesbaren Dateibytes. PDF und Word können über die Dateiauswahl übernommen werden, wenn die Zwischenablage sie nicht bereitstellt.
* JPG-/PNG-Bilder erhalten eine Vorschau. Andere unterstützte Formate zeigen Dateinamen und Dateigrösse.
* Anders als bei der Scan-Bearbeitung werden die ausgewählten Dateibytes nicht umgerechnet. Namen und Metadaten werden erst im bestehenden Übernahme-Ablauf festgelegt.
* Die vorhandenen Backend-Prüfungen bleiben zuständig. Frontend-Prüfungen dienen der schnellen Rückmeldung.

## References

* https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/read
* https://developer.mozilla.org/en-US/docs/Web/API/Element/paste_event
