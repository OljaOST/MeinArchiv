from io import BytesIO

from sqlalchemy.exc import SQLAlchemyError

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

from .datenbank import Dokument, db

PROJEKTORDNER = Path(__file__).resolve().parents[2]
load_dotenv(PROJEKTORDNER / ".env")

app = Flask(__name__)
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


@app.cli.command("init-db")
def init_db():
    db.create_all()
    click.echo("Die Datenbanktabellen sind bereit.")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/dokumente")
def dokumente():
    try:
        abfrage = db.select(
            Dokument.id,
            Dokument.dateiname,
        ).order_by(Dokument.id.desc())

        gespeicherte_dokumente = db.session.execute(abfrage).all()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Dokumente konnten nicht geladen werden."), 503

    return render_template(
        "dokumente.html",
        dokumente=gespeicherte_dokumente,
    )

@app.route("/dokumente/speichern", methods=["POST"])
def dokument_speichern():
    datei = request.files.get("dokument")

    if datei is None or not datei.filename:
        return jsonify(fehler="Bitte eine Datei auswählen."), 400

    dateiname = Path(datei.filename.replace("\\", "/")).name

    if not dateiname or len(dateiname) > 255:
        return jsonify(fehler="Der Dateiname ist ungültig oder zu lang."), 400

    erlaubte_endungen = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}

    if Path(dateiname).suffix.lower() not in erlaubte_endungen:
        return jsonify(fehler="Dieses Dateiformat wird nicht unterstützt."), 400

    inhalt = datei.read()

    if not inhalt:
        return jsonify(fehler="Die Datei ist leer."), 400

    dokument = Dokument(
        dateiname=dateiname,
        inhalt=inhalt,
    )

    try:
        db.session.add(dokument)
        db.session.commit()
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