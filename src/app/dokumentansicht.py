"""Detailansicht, Vorschau und bestätigtes Löschen abgelegter Dokumente."""

import os
import secrets
from io import BytesIO
from pathlib import Path

from flask import abort, jsonify, redirect, render_template, request, send_file, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import SQLAlchemyError

from .datenbank import Dokument, Kategorie, db
from .dokumentordner import ordner_url

# Lokal funktioniert die Bestätigung ohne zusätzliche Einrichtung. Für mehrere
# Serverprozesse muss FORMULAR_SCHLUESSEL als gemeinsames Geheimnis gesetzt werden.
_formular_schluessel = os.getenv("FORMULAR_SCHLUESSEL") or secrets.token_urlsafe(32)
_loesch_bestaetigung = URLSafeTimedSerializer(
    _formular_schluessel, salt="meinarchiv-dokument-loeschen"
)
_vorschau_typen = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}


def _lade_metadaten(dokument_id):
    return db.session.execute(
        db.select(
            Dokument.id,
            Dokument.dateiname,
            Dokument.kategorie_id,
            Dokument.firma,
            Dokument.ablagedatum,
            Kategorie.name.label("kategoriename"),
            db.func.length(Dokument.inhalt).label("groesse"),
        )
        .outerjoin(Kategorie, Dokument.kategorie_id == Kategorie.id)
        .where(Dokument.id == dokument_id, Dokument.ist_entwurf.is_(False))
    ).one_or_none()


def _datenbankfehler():
    db.session.rollback()
    return (
        render_template(
            "dokument_fehler.html",
            meldung=(
                "Das Dokument konnte momentan nicht geladen oder geändert werden. "
                "Bitte versuche es erneut."
            ),
        ),
        503,
    )


def dokument_anzeigen(dokument_id):
    try:
        dokument = _lade_metadaten(dokument_id)
    except SQLAlchemyError:
        return _datenbankfehler()
    if dokument is None:
        abort(404)

    endung = Path(dokument.dateiname).suffix.lower()
    return render_template(
        "dokument_detail.html",
        dokument=dokument,
        vorschau=(
            "bild"
            if endung in {".jpg", ".jpeg", ".png"}
            else "pdf" if endung == ".pdf" else None
        ),
    )


def dokument_vorschau_anzeigen(dokument_id, *, ist_entwurf=False):
    try:
        dokument = db.session.execute(
            db.select(Dokument.dateiname, Dokument.inhalt).where(
                Dokument.id == dokument_id,
                Dokument.ist_entwurf.is_(ist_entwurf),
            )
        ).one_or_none()
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(fehler="Die Vorschau konnte nicht geladen werden."), 503
    if dokument is None:
        abort(404)

    mimetype = _vorschau_typen.get(Path(dokument.dateiname).suffix.lower())
    if mimetype is None:
        return (
            jsonify(
                fehler=(
                    "Für dieses Format ist keine Browser-Vorschau verfügbar. "
                    "Bitte lade das Dokument herunter."
                )
            ),
            415,
        )

    antwort = send_file(
        BytesIO(dokument.inhalt),
        mimetype=mimetype,
        as_attachment=False,
        download_name=dokument.dateiname,
        max_age=0,
    )
    antwort.headers["X-Content-Type-Options"] = "nosniff"
    antwort.headers["X-Frame-Options"] = "SAMEORIGIN"
    antwort.headers["Cache-Control"] = "no-store"
    return antwort


def dokument_loeschen_bestaetigen(dokument_id):
    aus_ordner = request.args.get("aus_ordner") == "1"
    # Löschen über «Zuletzt abgelegt» führt danach zurück zur Startseite.
    von_start = request.args.get("von") == "start"
    if request.method == "POST":
        try:
            bestaetigung = _loesch_bestaetigung.loads(
                request.form.get("bestaetigung", ""), max_age=15 * 60
            )
        except (SignatureExpired, BadSignature):
            return (
                render_template(
                    "dokument_fehler.html",
                    meldung=(
                        "Die Bestätigung ist ungültig oder abgelaufen. "
                        "Öffne die Löschseite bitte erneut."
                    ),
                ),
                400,
            )

        if (
            bestaetigung != {"dokument_id": dokument_id}
            or request.form.get("loeschen") != "ja"
        ):
            return (
                render_template(
                    "dokument_fehler.html",
                    meldung="Bitte bestätige das Löschen auf der Löschseite.",
                ),
                400,
            )

        try:
            geloescht = db.session.execute(
                db.delete(Dokument)
                .where(
                    Dokument.id == dokument_id,
                    Dokument.ist_entwurf.is_(False),
                )
                .returning(Dokument.kategorie_id)
            ).one_or_none()
            if geloescht is None:
                db.session.rollback()
                abort(404)
            db.session.commit()
        except SQLAlchemyError:
            return _datenbankfehler()
        if von_start:
            ziel = url_for("index")
        elif aus_ordner:
            ziel = ordner_url(geloescht.kategorie_id)
        else:
            ziel = url_for("dokumente")
        return redirect(ziel, code=303)

    try:
        dokument = _lade_metadaten(dokument_id)
    except SQLAlchemyError:
        return _datenbankfehler()
    if dokument is None:
        abort(404)

    if von_start:
        zurueck, zurueck_text = url_for("index"), "Zurück zur Startseite"
    elif aus_ordner:
        zurueck, zurueck_text = ordner_url(dokument.kategorie_id), "Zurück zum Ordner"
    else:
        zurueck = url_for("dokument_detail", dokument_id=dokument_id)
        zurueck_text = "Zurück zum Dokument"

    return render_template(
        "dokument_loeschen.html",
        dokument=dokument,
        zurueck=zurueck,
        zurueck_text=zurueck_text,
        bestaetigung=_loesch_bestaetigung.dumps({"dokument_id": dokument_id}),
    )
