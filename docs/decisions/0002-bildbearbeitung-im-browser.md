# Scan-Fotos im Browser bearbeiten

Date: 2026-11-09

## Status

Accepted

## Context

MeinArchiv soll gemäss den Entwürfen Fotos vor der Ablage anzeigen und bearbeiten können. Die Anwendung nutzt Flask, HTML, CSS und JavaScript ohne Frontend-Buildschritt. Die Dokumentanalyse und die Übernahme erkannter Angaben sind bereits vorhanden.

## Options Considered

* Canvas im Browser: keine neue Abhängigkeit, Bearbeitung vor dem ersten Upload; Bildoperationen müssen selbst implementiert und getestet werden.
* Zusätzliche Bildbearbeitungsbibliothek: mehr fertige Werkzeuge, aber zusätzliche Abhängigkeit und Einarbeitung.
* Bildbearbeitung im Python-Backend: zentral ausführbar, benötigt jedoch einen früheren Upload und weitere Server-Endpunkte.

## Decision

Die bestehende, schrittweise Scan-Umsetzung wird auf Wunsch der Entwicklerin in einem zusammenhängenden Schritt erweitert. Drehen, rechteckiges Zuschneiden und Zurücksetzen erfolgen mit Canvas im Browser. Der vorhandene Flask-Endpunkt empfängt das bearbeitete Foto.

## Reasons

Die Umsetzung bleibt im vorhandenen Technologiestack und ist für das Lernprojekt nachvollziehbar. Vor dem Upload werden keine Bilddaten an einen Server gesendet. Die bestehende separate Freigabe vor der OpenAI-Anfrage bleibt erhalten.

## Consequences

* Fotos werden für die Bearbeitung auf maximal 2800 Pixel an der längsten Seite begrenzt und als JPEG mit Qualitätswert 0,92 hochgeladen. Transparente Bereiche werden weiss. Dies ist keine verlustfreie Archivierung des Originals.
* Der Zurücksetzen-Knopf stellt das zu Beginn geladene, gegebenenfalls verkleinerte Arbeitsbild wieder her.
* Der Zuschnitt ist rechteckig und wird über vier Randregler eingestellt. Automatische Kantenerkennung, Perspektivkorrektur und Mehrseitenscans sind in dieser Erweiterung nicht enthalten.
* Die Browserprüfung der Dateiendung und der 10-MB-Grenze ergänzt die vorhandenen Backend-Prüfungen. Sie ersetzt keine serverseitige Prüfung des tatsächlichen Dateiinhalts.
* Browsertests prüfen Ausrichtung, Ausschnitt, Reset, Übertragung der bearbeiteten Bilddaten, Fehlerzustände und mobile Darstellung. Sie verwenden künstliche Bilder und simulierte Upload-Antworten, keine echte OpenAI-Anfrage.
