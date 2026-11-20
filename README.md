# MeinArchiv

Dokumente automatisiert mit KI nach Kategorien ablegen und verwalten.

MeinArchiv entsteht als Semesterprojekt im Fach Softwareentwicklung. Die Webanwendung unterstützt die Ablage persönlicher Unterlagen. OpenAI erkennt eine Firma und eine passende vorhandene Kategorie. Die Anwendung erstellt daraus einen Dateinamenvorschlag, den die Person vor dem Speichern prüfen und ändern kann.

[Online-Version öffnen](https://meinarchiv.onrender.com/)

## Funktionen

- Dokumente mit der Kamera scannen und mehrere Seiten in einem PDF speichern.
- Scanseiten zuschneiden, drehen und vor dem Speichern prüfen.
- PDF-, JPG-, PNG- und Word-Dateien hochladen.
- Dokumente über die Zwischenablage einfügen, sofern der Browser die kopierte Datei bereitstellt.
- Dateinamen anhand von Ablagedatum, Dokumenttyp und Firma vorschlagen.
- Dokumente über Dateinamen suchen und in Kategorieordnern verwalten.
- Dokumente ansehen, herunterladen, verschieben, umbenennen und nach Bestätigung löschen.
- Kategorien erstellen, umbenennen und löschen.
- Abgelegte Dokumente mit Metadaten als ZIP exportieren.

Die Uploadgrenze beträgt insgesamt 10 MB pro Anfrage. Bei einem mehrseitigen Scan gilt sie für das gesamte PDF. Die Browser-Vorschau unterstützt Bilder und PDFs.

Der Server prüft bei jeder Datei, ob der Inhalt zum Format der Endung passt. Eine umbenannte Datei, etwa ein Programm mit der Endung `.pdf`, wird abgewiesen, bevor sie gespeichert oder an OpenAI gesendet wird. Die Begründung steht im [Entscheidungsprotokoll 0010](docs/decisions/0010-pruefung-des-dateiinhalts.md).

## Automatische Benennung

Die Anwendung verwendet das Schema `JJMMTT_Dokumenttyp_Firma.Dateiendung`.

```text
261117_Rechnung_Muster GmbH.pdf
```

Das Datum bezeichnet den Tag der Ablage. Beim Scannen dient die erste Aufnahme als Grundlage für den Namensvorschlag. Das fertige PDF enthält die ausgewählten Seiten in ihrer Aufnahmereihenfolge.

Die App übermittelt die Datei beim Hochladen beziehungsweise Einfügen zur Erkennung an OpenAI. Bei Scans übermittelt sie die erste Aufnahme. Liefert die KI keinen geeigneten Vorschlag, kann die Person den angezeigten Ersatznamen selbst ändern und das Dokument speichern.

## Dokumentation

- [Use Cases und Ablauf der Dokumentablage](docs/use-cases.md)
- [Applikationsarchitektur, Datenmodell und Technologieentscheidungen](docs/architektur.md)
- [Bisherige Entscheidungsprotokolle](docs/decisions/)

Die Entscheidungsprotokolle halten einzelne Entwicklungsstände fest. Die vorliegende README und die verlinkten Übersichten beschreiben den aktuellen Funktionsumfang.

## Technologien

| Bereich | Umsetzung |
| --- | --- |
| Benutzeroberfläche | HTML, CSS und JavaScript |
| HTML-Vorlagen | Jinja |
| Backend | Python und Flask |
| Datenbankzugriff | Flask-SQLAlchemy und psycopg |
| Datenhaltung | PostgreSQL |
| Schemaänderungen | Flask-Migrate und Alembic |
| Dokumenterkennung | OpenAI-API |
| PDF-Vorschau | PDF.js |
| Lokale Datenbank | Docker Compose |
| Tests | pytest, pytest-cov und GitHub Actions |
| Online-Bereitstellung | Render |

## Lokal starten

Vorausgesetzt sind Git, uv und Docker mit laufender Docker-Engine. Das Projekt verlangt Python ab Version 3.13. uv richtet die Projektumgebung ein.

### 1. Repository herunterladen

```bash
git clone https://github.com/OljaOST/MeinArchiv.git
cd MeinArchiv
uv sync
```

Wer das Projekt bereits lokal geöffnet hat, führt die weiteren Schritte in diesem Projektordner aus.

### 2. Lokale Konfiguration anlegen

Im Hauptordner eine Datei `.env` erstellen und eigene Werte eintragen.

```dotenv
POSTGRES_PASSWORD=hier_ein_eigenes_lokales_datenbankpasswort_eintragen
OPENAI_API_KEY=hier_den_eigenen_openai_api_schluessel_eintragen
FORMULAR_SCHLUESSEL=hier_einen_langen_zufaelligen_wert_eintragen
```

Die `.gitignore` schliesst `.env` vom Commit aus. Der OpenAI-Schlüssel ermöglicht die Online-Erkennung. `FORMULAR_SCHLUESSEL` hält Formularbestätigungen über Serverneustarts und mehrere Prozesse hinweg gültig.

### 3. PostgreSQL und Datenbanktabellen vorbereiten

```bash
docker compose up -d --wait db
uv run flask --app src/app db upgrade
```

Für eine neue Datenbank legt `db upgrade` die Tabellen über die vorhandenen Migrationen an. Bei einer bestehenden Installation führt der Befehl die noch ausstehenden Migrationen aus.

### 4. Flask starten

```bash
uv run flask --app src/app run --reload --host 127.0.0.1 --port 8000
```

Die Anwendung ist anschliessend unter [MeinArchiv lokal](http://127.0.0.1:8000/) erreichbar. Das Terminal bleibt für den laufenden Server geöffnet. Mit Ctrl + C lässt sich der Server stoppen. Falls Port 8000 belegt ist, kann der bisherige Server beendet oder ein anderer Port verwendet werden.

## Testing

Die automatischen Tests prüfen unter anderem die Benennung, KI-Anfragen mit simulierten Antworten, Uploads, Datenbankzugriff, Dokumentaktionen und den ZIP-Export. Die Integrationstests verwenden eine separate PostgreSQL-Testdatenbank auf Port 5433.

Im Projektordner zunächst die Testdatenbank starten.

```bash
docker compose -p meinarchiv-tests -f compose.test.yml up -d --wait
```

Im gleichen Terminal auf macOS oder Linux die Tests mit der Testdatenbank ausführen.

```bash
DATABASE_URL='postgresql+psycopg://meinarchiv_test:nur-fuer-tests@127.0.0.1:5433/meinarchiv_test' OPENAI_API_KEY='' uv run pytest
```

Die Testfixtures erstellen und entfernen Tabellen. Deshalb muss dieser Befehl die vorgesehene Testdatenbank verwenden. Nach dem Test lässt sich der Testcontainer beenden.

```bash
docker compose -p meinarchiv-tests -f compose.test.yml down
```

Vor einem Push den Code formatieren und prüfen. Die Einstellungen stammen aus `pyproject.toml`.

```bash
uv run black src tests scripts
uv run ruff check --fix src tests scripts
```

[GitHub Actions](https://github.com/OljaOST/MeinArchiv/actions) prüft bei Pushes und Pull Requests zuerst Code und Formatierung mit ruff und black und führt danach dieselben Tests automatisch aus. Praktische Browserprüfungen ergänzen sie bei Kamera, Zwischenablage, Zuschnitt und PDF-Seitennavigation.

## Online-Betrieb

Render stellt die Webanwendung unter [meinarchiv.onrender.com](https://meinarchiv.onrender.com/) bereit. Im Betrieb verbindet `DATABASE_URL` die Anwendung mit PostgreSQL. Die Zugangsdaten und der OpenAI-Schlüssel gehören in die Umgebungsvariablen des Webdienstes. `FORMULAR_SCHLUESSEL` muss für alle Prozesse denselben Wert besitzen.

Schemaänderungen erfordern zusätzlich das Ausführen der vorhandenen Migrationen gegen die Datenbank des Webdienstes. Der lokale Docker-Datenbankcontainer dient der lokalen Entwicklung.

## Geplante Erweiterungen

- Speicherort in den Einstellungen auswählen.
- KI-Modell beziehungsweise Anbieter in den Einstellungen auswählen.
- Bausteine und Reihenfolge der Dokumentbenennung konfigurieren.
- Login mit Benutzerkonten und persönlichen Archiven ergänzen.

Der aktuelle MVP verwendet ein gemeinsames Archiv und die konfigurierte OpenAI-Anbindung.
