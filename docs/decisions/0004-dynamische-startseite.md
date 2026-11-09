# Startseite aus Datenbankdaten erzeugen

Date: 2026-11-09

## Status

Accepted

## Context

Die Startseite soll gemäss Vorlage Suche, Kategorien und zuletzt abgelegte Dokumente zeigen. Die Entwicklerin wünscht zusammenhängende Umsetzungsschritte. Dokumente und Kategorien liegen bereits in PostgreSQL; Uploadentwürfe dürfen nicht als abgelegte Dokumente erscheinen.

## Options Considered

* Flask/Jinja: Daten beim Seitenaufruf abfragen und HTML erzeugen; passt zu den vorhandenen Dokument- und Kategorieansichten.
* JavaScript mit zusätzlichen JSON-Endpunkten: unabhängig nachladbare Bereiche, aber mehr Schnittstellen und Zustände für den bisherigen Lernstand.
* Statische Beispieldaten: schnell gestaltbar, erfüllen den gewünschten produktiven Ablauf jedoch nicht.

## Decision

Die vorhandene index-Route bleibt unter demselben Namen bestehen und delegiert an startseite.py. Die Abfragen und die Kategorieansicht liegen in diesem separaten Modul. Jinja erzeugt die Startseite. Eine zusätzliche Route zeigt archivierte Dokumente einer gewählten Kategorie und ermöglicht eine Suche innerhalb dieser Auswahl.

## Reasons

Die Lösung verwendet den bestehenden Flask-/SQLAlchemy-Stack und braucht keinen Buildschritt oder eine neue Abhängigkeit. Die grösser werdende __init__.py erhält nur eine Delegation und eine zusätzliche kurze Route. Geschäftsregeln für Entwürfe, Abfragen und Filterung bleiben im Backend.

## Consequences

* static/index.html wird nicht mehr für die Startseiten-Route verwendet. Künftige Änderungen der Startseite erfolgen in templates/startseite.html.
* Kategorien enthalten Zähler für abgelegte Dokumente. Kategorien ohne Dokumente bleiben sichtbar. Der Gesamtzähler enthält auch abgelegte Dokumente ohne Kategorie.
* Zuletzt abgelegt zeigt maximal fünf archivierte Dokumente nach Ablagedatum absteigend und ID absteigend. Legacy-Dokumente ohne Ablagedatum stehen dahinter. Eine sekundengenaue Reihenfolge der endgültigen Übernahme ist ohne zusätzliches Zeitstempelfeld nicht möglich.
* Dokumentinhalte werden für die Übersicht nicht aus der Datenbank geladen.
* Datenbankfehler werden mit Status 503 und einer verständlichen Meldung angezeigt, nicht als scheinbar leeres Archiv.
* Die Suche auf der Startseite verwendet die bestehende Dateinamensuche. Es wird keine Volltextsuche im Dokumentinhalt eingeführt.
* Es ist keine Datenbankmigration erforderlich. Integrationstests laufen ausschliesslich auf der bereits vorgesehenen separaten Testdatenbank.
