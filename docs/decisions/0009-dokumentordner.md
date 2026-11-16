# Dokumentordner und Verschieben

Date: 2026-11-11

## Status

Accepted

## Context

Die Vorlage «Dokumente verwalten» zeigt unter «Meine Dokumente» eine Liste von Ordnern mit Dokumentzahlen. Die Nutzerin möchte Dateien aus einem Ordner in einen anderen verschieben können.

## Options considered

* Kategorien als Ordner darstellen. Eine vorhandene Zuordnung reicht aus.
* Eine eigene Ordnerstruktur anlegen. Damit wären beispielsweise Unterordner möglich, zusätzliche Datenstrukturen wären nötig.

## Decision

Die vorhandenen Kategorien bilden die Ordner. Dokumente ohne Zuordnung erhalten die Ansicht «Ohne Kategorie». Die Aktion «Verschieben» ändert die Kategorie des abgelegten Dokuments. Ein Formular mit dem ursprünglichen Ordner verhindert das unbemerkte Überschreiben einer neueren Verschiebung.

## Reasons

Die Vorlage verlangt eine Ebene mit Kategorieordnern. Die bestehende Zuordnung, Suche und Kategorieverwaltung decken diesen Umfang ab. Der Ordnerwechsel kann deshalb mit einer Änderung der Kategorie gespeichert werden.

## Consequences

Dokumentzahlen zählen abgelegte Dateien. Entwürfe bleiben in «Offene Uploads». Die Suche auf «Meine Dokumente» durchsucht die abgelegten Dateien aller Ordner. Beim Verschieben bleiben der vorhandene Dateiname und Dateiinhalt erhalten. Dateinamen lassen sich im Ordner über «Umbenennen» ändern. Eine Datenbankmigration ist nicht erforderlich.
