# Einstellungen mit Archivstatus und Dokumentexport

Date: 2026-11-09

## Status

Accepted

## Context

Die App-Vorlage enthält einen Einstellungsbereich. Für den vereinbarten MVP sind Speicherung in der Datenbank und Online-Erkennung durch OpenAI gewählt. Die Entwicklerin möchte die Umsetzung fortsetzen und den verbleibenden Aufwand einschätzen. Nach den Kernfunktionen wird die Einsicht in den aktuellen Betriebszustand und eine lokale Kopie der Dokumente ergänzt.

## Options Considered

* Read-only Statusseite plus ZIP-Export: verwendet den bestehenden Stack und zeigt nur tatsächlich verfügbare Funktionen.
* Vollständige Auswahl verschiedener Cloudanbieter und lokaler KI-Modelle: deutlich grösserer Umfang ausserhalb der bisherigen MVP-Auswahl.
* Vollständiges PostgreSQL-Backup samt Wiederherstellung: nützlich für den Betrieb, erfordert jedoch zusätzliche Werkzeuge, Berechtigungen und einen gesonderten Wiederherstellungsablauf.

## Decision

Ein Modul einstellungen.py liefert die Einstellungsseite mit Archivstatistik und dem Status eines hinterlegten KI-Schlüssels. Ein separater GET-Endpunkt exportiert endgültig abgelegte Dateien und ihre Metadaten als ZIP. Der Zugang erfolgt über ein Zahnrad auf der Startseite. Die bisherigen Speicher- und KI-Verfahren werden nicht umgestellt.

## Reasons

Die Seite ergänzt den vereinbarten MVP ohne vorgetäuschte Provider-Umschaltung. Ein Dokumentexport lässt sich mit Standardbibliothek, Flask und SQLAlchemy umsetzen und unabhängig von einer Cloudbereitstellung verwenden. Nutzer erhalten ihre Dateien in einem gewöhnlichen Archivformat.

## Consequences

* Die Statistik zeigt abgelegte Dokumente, offene Uploadentwürfe, Kategorien und die Summe der abgelegten Dateiinhalte. Sie ist keine Messung der gesamten physischen Datenbankgrösse.
* Der KI-Status prüft nur das Vorhandensein eines Schlüssels. Er zeigt keinen Schlüsselwert und löst keine OpenAI-Anfrage aus.
* Exportiert werden ausschliesslich abgelegte Dokumente. Leere Kategorien und vorhandene Legacy-Metadaten bleiben in metadaten.json nachvollziehbar.
* Je Dokument wird ein eigener Ordner unter seiner ID verwendet. Gleichnamige Dateien kollidieren nicht; gespeicherte Pfadteile und problematische Dateinamen werden für ZIP-Einträge bereinigt. Der ursprüngliche Name bleibt in den Metadaten erhalten.
* Die Dateibytes bleiben unverändert. Grösse und SHA-256-Prüfsumme werden mitgeschrieben.
* Daten werden zeilenweise gelesen. Das Archiv nutzt bis zu 8 MB Arbeitsspeicher und danach eine temporäre Datei. Die ZIP-Datei wird vor der HTTP-Antwort fertiggestellt, sodass ein erkannter Exportfehler nicht als unvollständiger erfolgreicher Download ausgeliefert wird.
* Der Export ist kein vollständiges Datenbank-Backup und beinhaltet keine Wiederherstellung. Während eines Exports können Metadaten durch andere Nutzer geändert werden; ein vollständiger transaktionsübergreifender Datenbank-Snapshot wird nicht zugesichert.
* Ein leeres Archiv liefert ein gültiges ZIP mit Metadaten und Erklärung. Datenbank- und Dateifehler führen zu einer verständlichen Meldung mit Status 503.
* Die exportierten Daten sind dieselben privaten Archivdaten wie in der Dokumentverwaltung. Der gemeinsame Zugangsschutz bleibt der nächste eigenständige Arbeitsschritt vor einer Online-Veröffentlichung.
* Keine Schemaänderung und keine zusätzliche Paketinstallation nötig.
