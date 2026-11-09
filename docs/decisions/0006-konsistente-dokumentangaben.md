# Dokumentangaben und Dateiname gemeinsam bearbeiten

Date: 2026-11-09

## Status

Accepted

## Context

Die ursprüngliche Vorgabe verlangt Dateinamen aus Ablagedatum, Dokumenttyp und Firma. Die bisherige manuelle Kategorieänderung aktualisiert nur die Zuordnung. Der Dateiname kann dadurch von den angezeigten Angaben abweichen. Die Entwicklerin möchte zusammenhängende Umsetzungsschritte bei weiterhin verständlicher Implementierung.

## Options Considered

* Firma und Kategorie gemeinsam auf einer Flask-/Jinja-Seite bearbeiten und den Namen mit der vorhandenen Python-Funktion neu berechnen.
* Getrennte Endpunkte für einzelne Felder: mehr Wege, die denselben Dateinamen konsistent halten müssten.
* Namen ausschliesslich nach einer erneuten KI-Analyse ändern: unnötige Online-Anfrage bei manuellen Korrekturen.

## Decision

Die bisherige dokument_kategorie-Route bleibt mit ihrem Namen und Pfad erhalten. Sie delegiert künftig an dokumentbearbeitung.py. Das Formular bearbeitet Firma und Kategorie, ergänzt gegebenenfalls ein fehlendes Legacy-Ablagedatum und erzeugt den Dateinamen über die vorhandene Funktion erstelle_dateinamen. Die Dateibytes werden nicht verändert.

## Reasons

Der vorhandene Dateinamen-Code bleibt die zentrale Regel. Manuelle Korrekturen brauchen keine KI-Anfrage. Firma, Kategorie, Datum und Name werden in einer Transaktion gespeichert. Ein gezieltes Einbindungsskript vermeidet das manuelle Austauschen eines langen Funktionsblocks durch die Anfängerin.

## Consequences

* Ein bestehendes Ablagedatum bleibt unverändert; auch ein abweichendes mitgesendetes Datum ersetzt es nicht. Bei Legacy-Dokumenten ohne Datum wird ein gültiges, nicht zukünftiges Ablagedatum benötigt.
* Ohne Kategorie wird Dokument als Dokumenttyp im Namen verwendet. Sonst gelten die bestehenden Regeln, etwa Verträge zu Vertrag.
* Nur abgelegte Dokumente werden bearbeitet. Entwürfe bleiben im bisherigen KI-Übernahme-Ablauf.
* Ein 15 Minuten gültiger signierter Formularcode ist an Dokument-ID und ursprünglichen Metadatenstand gebunden. Veraltete Eingaben überschreiben einen inzwischen geänderten Stand nicht ohne eine neue bewusste Bestätigung. Eine Zeilensperre schützt den eigentlichen Speichervorgang.
* Das neue Formular nutzt für mehrere Serverprozesse FORMULAR_SCHLUESSEL wie die Löschbestätigung. Lokal wird ohne zusätzliche Einrichtung ein pro Prozess zufälliger Schlüssel verwendet. Dies ersetzt keine künftige Anmeldung oder Berechtigungsprüfung.
* Der alte Pfad /dokumente/<id>/kategorie zeigt jetzt das vollständige Angabenformular. Ein noch vor der Aktualisierung geöffnetes altes Formular ohne Bestätigungscode wird abgewiesen.
* Das Einbindungsskript verändert nur die eindeutige Funktion dokument_kategorie und ergänzt den Import. Es prüft den erzeugten Python-Code vor dem atomaren Austausch und sichert das Original im temporären Verzeichnis. Die Datenbank wird nicht berührt.
* Es ist keine Schemaänderung erforderlich. Neue Tests verwenden wie bisher nur die separate PostgreSQL-Testdatenbank; Skripttests verwenden temporäre Projektdateien.
