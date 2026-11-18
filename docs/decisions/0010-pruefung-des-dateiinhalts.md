# Serverseitige Prüfung des Dateiinhalts

Date: 2026-11-18

## Status

Proposed

## Context

MeinArchiv nimmt PDF-, JPG-, PNG-, DOC- und DOCX-Dateien über Scannen, Hochladen und Einfügen an. Alle drei Wege senden die Datei an dieselbe Route `/dokumente/vorbereiten`. Bisher prüfte der Server beim Hochladen und Einfügen nur die Dateiendung. Den Inhalt prüfte er nur, wenn das Formularfeld `quelle` den Wert `scan` hatte.

Die Endung ist ein Teil des Dateinamens und wird vom Browser mitgeschickt. Dasselbe gilt für das Feld `quelle`. Ein Test zeigte, dass eine in `rechnung.pdf` umbenannte Programmdatei angenommen, als Entwurf gespeichert und zur Erkennung an OpenAI gesendet wurde. Die Browser-Prüfung über das `accept`-Attribut der Dateiauswahl lässt sich umgehen. ADR 0002 hält bereits fest, dass sie keine serverseitige Prüfung des Inhalts ersetzt.

Zusätzlich war die Liste der erlaubten Formate an fünf Stellen im Code wiederholt: zweimal in `__init__.py` sowie in `dokumentbearbeitung.py`, `ki.py` und `dokumentimport.py` (als eigene PDF-Prüfung für Scans).

## Options Considered

* Nur die Endung prüfen: kein Aufwand, aber der Inhalt bleibt ungeprüft.
* Bibliothek `python-magic`: erkennt sehr viele Formate, braucht aber die Systembibliothek libmagic. Das erschwert die Einrichtung unter Windows und im Docker-Image und fügt eine Abhängigkeit für nur fünf Formate hinzu.
* Eigene Prüfung der Dateisignatur: Fast jedes Format beginnt mit festen Erkennungsbytes. Für fünf Formate reichen wenige, gut testbare Zeilen ohne neue Abhängigkeit.
* Dateien vollständig einlesen, zum Beispiel jedes PDF mit einer PDF-Bibliothek öffnen: genauer, aber deutlich aufwendiger und langsamer.

## Decision

Das neue Modul `src/app/dateiformate.py` enthält die zentrale Liste der erlaubten Formate (`DATEIFORMATE`, `ERLAUBTE_ENDUNGEN`) und die Funktion `inhalt_passt_zur_endung()`. Die Route `/dokumente/vorbereiten` prüft damit jede Datei unabhängig vom Feld `quelle`, bevor ein Entwurf gespeichert oder OpenAI angefragt wird. Die übrigen Module verwenden die zentrale Liste.

Die Route `/dokumente/speichern` wurde entfernt. Weder das Frontend noch ein Test verwendete sie. Sie war aber per POST erreichbar und hätte Dateien ohne die neue Prüfung im Archiv abgelegt.

## Reasons

Sicherheitsrelevante Prüfungen gehören ins Backend, weil der Client Dateinamen und Formularfelder frei bestimmen kann. Eine zentrale Liste verhindert, dass eine neue Erweiterung an einer der bisher fünf Stellen vergessen wird. Die Signaturprüfung bleibt ohne neue Abhängigkeit verständlich und lässt sich ohne Datenbank mit Unit-Tests prüfen.

## Consequences

* Signaturen: PDF `%PDF-`, PNG `89 50 4E 47 0D 0A 1A 0A`, JPEG `FF D8 FF`, DOC `D0 CF 11 E0 A1 B1 1A E1`, DOCX `PK` (ZIP).
* Bei PDF darf die Kennung `%PDF-` laut Spezifikation innerhalb der ersten 1024 Bytes stehen. PDF-Reader akzeptieren solche Dateien ebenfalls.
* Bei DOCX prüft die Anwendung zusätzlich, ob das ZIP die Datei `word/document.xml` enthält. Ein beliebiges ZIP wird abgewiesen. Dafür wird nur das Inhaltsverzeichnis des Archivs gelesen, nicht entpackt.
* Alte DOC-Dateien teilen ihre Signatur mit alten Excel- und PowerPoint-Dateien. Diese lassen sich nicht unterscheiden.
* Die Prüfung ist kein Virenscanner. Ein echtes PDF kann weiterhin schädliche Inhalte enthalten. Sie stellt nur sicher, dass eine Datei dem angegebenen Format entspricht.
* Bereits gespeicherte Dokumente werden nicht nachträglich geprüft.
* Die Vorschau-Formate in `dokumentansicht.py` bleiben eine eigene Liste. Sie beantwortet eine andere Frage, nämlich welche Formate der Browser anzeigen kann.
* Die Browser-Einschränkung `accept` in `hochladen.html` bleibt als Komfort für die Dateiauswahl bestehen.
