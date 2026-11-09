from flask_migrate import Migrate

from io import BytesIO

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from datetime import datetime

from zoneinfo import ZoneInfo

from .dateinamen import erstelle_dateinamen

from openai import APIError, OpenAI

from .ki import erkenne_dokument

import os
from pathlib import Path

import click
from dotenv import load_dotenv

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from sqlalchemy import URL

from .datenbank import Dokument, Kategorie, db

PROJEKTORDNER = Path(__file__).resolve().parents[2]
load_dotenv(PROJEKTORDNER / ".env")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    drivername="postgresql+psycopg",
    username="meinarchiv",
    password=os.environ["POSTGRES_PASSWORD"],
    host="127.0.0.1",
    port=5432,
    database="meinarchiv",
)

db.init_app(app)

migrate = Migrate(
    app,
    db,
    directory=str(PROJEKTORDNER / "migrations"),
)

@app.cli.command("init-db")
def init_db():
    db.create_all()
    click.echo("Die Datenbanktabellen sind bereit.")


@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/dokumente")
def dokumente():
    suche = request.args.get("q", "").strip()

    try:
        dokument_abfrage = (
            db.select(
                Dokument.id,
                Dokument.dateiname,
                Kategorie.name.label("kategoriename"),
            )
            .outerjoin(
                Kategorie,
                Dokument.kategorie_id == Kategorie.id,
            )
            .order_by(Dokument.id.desc())
        )

        if suche:
            dokument_abfrage = dokument_abfrage.where(
                Dokument.dateiname.icontains(suche, autoescape=True)
            )

        gespeicherte_dokumente = db.session.execute(dokument_abfrage).all()

        kategorie_abfrage = db.select(
            Kategorie.id,
            Kategorie.name,
        ).order_by(Kategorie.name)

        gespeicherte_kategorien = db.session.execute(kategorie_abfrage).all()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Übersicht konnte nicht geladen werden."), 503

    return render_template(
        "dokumente.html",
        dokumente=gespeicherte_dokumente,
        kategorien=gespeicherte_kategorien,
        suche=suche,
    )

@app.route("/dokumente/speichern", methods=["POST"])
def dokument_speichern():
    datei = request.files.get("dokument")

    if datei is None or not datei.filename:
        return jsonify(fehler="Bitte eine Datei auswählen."), 400

    originalname = Path(datei.filename.replace("\\", "/")).name

    if not originalname or len(originalname) > 255:
        return jsonify(fehler="Der Dateiname ist ungültig oder zu lang."), 400

    endung = Path(originalname).suffix.lower()
    erlaubte_endungen = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}

    if endung not in erlaubte_endungen:
        return jsonify(fehler="Dieses Dateiformat wird nicht unterstützt."), 400

    firma = request.form.get("firma", "").strip()

    if not firma or len(firma) > 120:
        return jsonify(
            fehler="Bitte eine Firma mit 1 bis 120 Zeichen eingeben."
        ), 400

    inhalt = datei.read()

    if not inhalt:
        return jsonify(fehler="Die Datei ist leer."), 400

    kategorie_wert = request.form.get("kategorie_id", "")

    try:
        kategorie_id = int(kategorie_wert) if kategorie_wert else None
    except ValueError:
        return jsonify(fehler="Bitte eine gültige Kategorie auswählen."), 400

    try:
        kategoriename = "Dokument"

        if kategorie_id is not None:
            kategorie = db.session.get(Kategorie, kategorie_id)

            if kategorie is None:
                return jsonify(
                    fehler="Die ausgewählte Kategorie existiert nicht mehr."
                ), 400

            kategoriename = kategorie.name

        ablagedatum = datetime.now(ZoneInfo("Europe/Zurich")).date()

        dateiname = erstelle_dateinamen(
            ablagedatum,
            kategoriename,
            firma,
            endung,
        )

        dokument = Dokument(
            dateiname=dateiname,
            inhalt=inhalt,
            firma=firma,
            ablagedatum=ablagedatum,
            kategorie_id=kategorie_id,
        )

        db.session.add(dokument)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            fehler="Die Zuordnung konnte nicht gespeichert werden. "
            "Bitte die Seite neu laden."
        ), 409
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Datei konnte nicht gespeichert werden."), 503

    return redirect(url_for("dokumente"), code=303)

@app.route("/dokumente/<int:dokument_id>/download")
def dokument_download(dokument_id):
    try:
        dokument = db.session.get(Dokument, dokument_id)
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Das Dokument konnte nicht geladen werden."), 503

    if dokument is None:
        abort(404)

    return send_file(
        BytesIO(dokument.inhalt),
        as_attachment=True,
        download_name=dokument.dateiname,
        mimetype="application/octet-stream",
    )

@app.route("/kategorien")
def kategorien():
    try:
        abfrage = db.select(
            Kategorie.id,
            Kategorie.name,
        ).order_by(Kategorie.name)

        gespeicherte_kategorien = db.session.execute(abfrage).all()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Kategorien konnten nicht geladen werden."), 503

    return render_template(
        "kategorien.html",
        kategorien=gespeicherte_kategorien,
    )


@app.route("/kategorien/speichern", methods=["POST"])
def kategorie_speichern():
    name = request.form.get("name", "").strip()

    if not name or len(name) > 60:
        return jsonify(
            fehler="Bitte einen Kategorienamen mit 1 bis 60 Zeichen eingeben."
        ), 400

    kategorie = Kategorie(name=name)

    try:
        db.session.add(kategorie)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(fehler="Diese Kategorie ist bereits vorhanden."), 409
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Kategorie konnte nicht gespeichert werden."), 503

    return redirect(url_for("kategorien"), code=303)

@app.route(
    "/dokumente/<int:dokument_id>/kategorie",
    methods=["GET", "POST"],
)
def dokument_kategorie(dokument_id):
    kategorie_id = None

    if request.method == "POST":
        kategorie_wert = request.form.get("kategorie_id", "")

        try:
            kategorie_id = int(kategorie_wert) if kategorie_wert else None
        except ValueError:
            return jsonify(fehler="Bitte eine gültige Kategorie auswählen."), 400

    try:
        dokument_abfrage = db.select(
            Dokument.id,
            Dokument.dateiname,
            Dokument.kategorie_id,
        ).where(Dokument.id == dokument_id)

        dokument = db.session.execute(dokument_abfrage).one_or_none()

        if dokument is None:
            abort(404)

        if request.method == "POST":
            if kategorie_id is not None:
                kategorie = db.session.get(Kategorie, kategorie_id)

                if kategorie is None:
                    return jsonify(
                        fehler="Die ausgewählte Kategorie existiert nicht mehr."
                    ), 400

            aenderung = (
                db.update(Dokument)
                .where(Dokument.id == dokument_id)
                .values(kategorie_id=kategorie_id)
            )

            ergebnis = db.session.execute(aenderung)

            if ergebnis.rowcount != 1:
                db.session.rollback()
                abort(404)

            db.session.commit()
            return redirect(url_for("dokumente"), code=303)

        kategorie_abfrage = db.select(
            Kategorie.id,
            Kategorie.name,
        ).order_by(Kategorie.name)

        kategorien = db.session.execute(kategorie_abfrage).all()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            fehler="Die Zuordnung konnte nicht gespeichert werden. "
            "Bitte die Seite neu laden."
        ), 409
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(
            fehler="Die Kategorie konnte nicht geladen oder geändert werden."
        ), 503

    return render_template(
        "dokument_kategorie.html",
        dokument=dokument,
        kategorien=kategorien,
    )

@app.route(
    "/kategorien/<int:kategorie_id>/bearbeiten",
    methods=["GET", "POST"],
)
def kategorie_bearbeiten(kategorie_id):
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name or len(name) > 60:
            return jsonify(
                fehler="Bitte einen Kategorienamen mit 1 bis 60 Zeichen eingeben."
            ), 400

    try:
        kategorie = db.session.get(Kategorie, kategorie_id)

        if kategorie is None:
            abort(404)

        if request.method == "POST":
            kategorie.name = name
            db.session.commit()

            return redirect(url_for("kategorien"), code=303)
    except IntegrityError:
        db.session.rollback()
        return jsonify(fehler="Dieser Kategoriename ist bereits vergeben."), 409
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(
            fehler="Die Kategorie konnte nicht geladen oder geändert werden."
        ), 503

    return render_template(
        "kategorie_bearbeiten.html",
        kategorie=kategorie,
    )

@app.route(
    "/kategorien/<int:kategorie_id>/loeschen",
    methods=["GET", "POST"],
)
def kategorie_loeschen(kategorie_id):
    try:
        kategorie = db.session.get(Kategorie, kategorie_id)

        if kategorie is None:
            abort(404)

        if request.method == "POST":
            db.session.delete(kategorie)
            db.session.commit()

            return redirect(url_for("kategorien"), code=303)

        anzahl_abfrage = db.select(
            db.func.count(Dokument.id)
        ).where(Dokument.kategorie_id == kategorie_id)

        anzahl_dokumente = db.session.scalar(anzahl_abfrage)
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(
            fehler="Die Kategorie konnte nicht geladen oder gelöscht werden."
        ), 503

    return render_template(
        "kategorie_loeschen.html",
        kategorie=kategorie,
        anzahl_dokumente=anzahl_dokumente,
    )

@app.cli.command("ki-test")
def ki_test():
    if not os.getenv("OPENAI_API_KEY"):
        raise click.ClickException(
            "OPENAI_API_KEY wurde nicht gefunden. Bitte die .env prüfen."
        )

    try:
        with OpenAI(timeout=30.0, max_retries=0) as client:
            antwort = client.responses.create(
                model="gpt-5.4-mini",
                input="Antworte ausschließlich mit: Verbindung erfolgreich.",
                reasoning={"effort": "none"},
                max_output_tokens=100,
                store=False,
            )
    except APIError as fehler:
        status = getattr(fehler, "status_code", None)

        raise click.ClickException(
            f"OpenAI-Anfrage fehlgeschlagen. "
            f"Fehlertyp: {type(fehler).__name__}, HTTP-Status: {status}"
        ) from None

    if not antwort.output_text.strip():
        raise click.ClickException("OpenAI hat keinen Antworttext geliefert.")

    click.echo(antwort.output_text)

@app.route(
    "/dokumente/<int:dokument_id>/analysieren",
    methods=["GET", "POST"],
)
def dokument_analysieren(dokument_id):
    ergebnis = None
    fehler = None
    status = 200

    try:
        dokument_abfrage = db.select(
            Dokument.id,
            Dokument.dateiname,
        ).where(Dokument.id == dokument_id)

        dokument = db.session.execute(dokument_abfrage).one_or_none()

        if dokument is None:
            abort(404)

        if request.method == "POST":
            if request.form.get("freigabe") != "ja":
                return jsonify(
                    fehler="Bitte die Übermittlung an OpenAI bestätigen."
                ), 400

            if not os.getenv("OPENAI_API_KEY"):
                return jsonify(
                    fehler="Der OpenAI-API-Schlüssel fehlt."
                ), 503

            inhalt_abfrage = db.select(
                Dokument.inhalt
            ).where(Dokument.id == dokument_id)

            inhalt = db.session.scalar(inhalt_abfrage)

            kategorien = db.session.scalars(
                db.select(Kategorie.name).order_by(Kategorie.name)
            ).all()

            # Datenbank-Lesevorgang vor der Online-Anfrage beenden.
            db.session.rollback()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(
            fehler="Das Dokument konnte nicht geladen werden."
        ), 503

    if request.method == "POST":
        try:
            ergebnis = erkenne_dokument(
                inhalt,
                Path(dokument.dateiname).suffix,
                kategorien,
            )
        except (APIError, ValueError) as ausnahme:
            fehler = (
                "Die KI-Analyse konnte nicht abgeschlossen werden. "
                f"Fehlertyp: {type(ausnahme).__name__}"
            )
            status = 502

    return render_template(
        "dokument_analysieren.html",
        dokument=dokument,
        ergebnis=ergebnis,
        fehler=fehler,
    ), status

