# Dokumentansicht und bestätigtes Löschen

Date: 2026-11-09

## Status

Accepted

## Context

Die Dokumentverwaltung soll abgelegte Unterlagen anzeigen und deren Entfernung ermöglichen. Kategorien und Uploadentwürfe werden bereits getrennt verwaltet. Die Entwicklerin setzt die App in grösseren zusammenhängenden Schritten um.

## Options Considered

* Separate serverseitige Detail- und Bestätigungsseiten mit Flask/Jinja: passen zu den bestehenden Ansichten und funktionieren ohne zusätzliche JavaScript-Bibliothek.
* JavaScript-Dialoge und JSON-Endpunkte: kompaktere Interaktion, benötigen aber mehr clientseitige Zustände.
* Sofortiges Löschen über einen Link: zu leicht versehentlich auslösbar und für GET-Anfragen ungeeignet.

## Decision

Ein separates Modul dokumentansicht.py übernimmt Detailansicht, Browser-Vorschau und bestätigtes Löschen. Die bestehende app-Instanz erhält drei kurze delegierende Routen. Neue Öffnen-Aktionen verbinden Dokumentliste, Startseite und Kategorieansichten mit der Detailseite.

## Reasons

Die Funktionen nutzen die vorhandenen Modelle und den bisherigen Technologiestack. Eine Bestätigungsseite, Checkbox und ein zeitlich begrenzter signierter Code machen die Löschabsicht konkret. Vorschau und Download sind getrennte Endpunkte mit korrekter Content-Disposition.

## Consequences

* Neue Detail-, Vorschau- und Löschrouten akzeptieren ausschliesslich abgelegte Dokumente. Uploadentwürfe bleiben im bestehenden Fortsetzen-/Verwerfen-Ablauf.
* GET-Anfragen löschen nichts. Löschen erfolgt nur durch POST nach gültiger, an die Dokument-ID gebundener Bestätigung und Checkbox.
* Löschen entfernt die Datei und ihre Metadaten dauerhaft. Es gibt in diesem Schritt keinen Papierkorb. Kategorien und andere Dokumente bleiben bestehen.
* Der Löschcode ist 15 Minuten gültig. Ein Prozess erzeugt lokal einen zufälligen Schlüssel. Für mehrere Serverprozesse muss FORMULAR_SCHLUESSEL als gemeinsames geheimes Umgebungssetting gesetzt werden. Ohne festen Schlüssel werden alte Codes nach einem Prozessneustart ungültig.
* Die Bestätigung schützt die neue Löschaktion; sie führt kein Anmelde- oder Berechtigungssystem für die gesamte Anwendung ein. Dieses Thema gehört gesondert zur Vorbereitung der Online-Version.
* Bilder und PDFs erhalten eine Inline-Vorschau mit explizitem MIME-Type und nosniff. Word-Dateien bleiben herunterladbar. Der Browser bestimmt, ob ein PDF eingebettet dargestellt werden kann; ein separater Vorschau-Link und Download bleiben verfügbar.
* Detailabfragen laden Metadaten und Dateigrösse, nicht den gesamten Dateiinhalt. Erst der Vorschau-Endpunkt liest die gespeicherten Dateibytes.
* Keine Schemaänderung und keine zusätzliche Paketinstallation nötig: itsdangerous ist bereits eine Abhängigkeit von Flask.
