"""Angaben eines abgelegten Dokuments bearbeiten und den Namen aktualisieren."""

import hashlib
import json
import os
import secrets
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import abort, redirect, render_template, request, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .dateinamen import erstelle_dateinamen
from .datenbank import Dokument, Kategorie, db

_bearbeitungs_bestaetigung = URLSafeTimedSerializer(
    os.getenv("FORMULAR_SCHLUESSEL") or secrets.token_urlsafe(32),
    salt="meinarchiv-dokument-bearbeiten",
)


def _datenstand(dokument):
    daten = [
        dokument.dateiname,
        dokument.firma,
        dokument.kategorie_id,
        dokument.ablagedatum.isoformat() if dokument.ablagedatum else None,
    ]
    return hashlib.sha256(json.dumps(daten).encode("utf-8")).hexdigest()


def dokument_angaben_bearbeiten(dokument_id):
    try:
        abfrage = db.select(
            Dokument.id,
            Dokument.dateiname,
            Dokument.firma,
            Dokument.kategorie_id,
            Dokument.ablagedatum,
        ).where(Dokument.id == dokument_id, Dokument.ist_entwurf.is_(False))
        if request.method == "POST":
            abfrage = abfrage.with_for_update()
        dokument = db.session.execute(abfrage).one_or_none()
        if dokument is None:
            abort(404)
        kategorien = db.session.execute(
            db.select(Kategorie.id, Kategorie.name).order_by(
                db.func.lower(Kategorie.name), Kategorie.id
            )
        ).all()
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "dokument_fehler.html",
                meldung=(
                    "Die Angaben konnten momentan nicht geladen werden. "
                    "Bitte versuche es erneut."
                ),
            ),
            503,
        )

    heute = datetime.now(ZoneInfo("Europe/Zurich")).date()
    werte = {
        "firma": dokument.firma or "",
        "kategorie_id": str(dokument.kategorie_id) if dokument.kategorie_id else "",
        "ablagedatum": dokument.ablagedatum.isoformat() if dokument.ablagedatum else "",
    }
    stand = _datenstand(dokument)

    def formular(fehler=None, status=200):
        return (
            render_template(
                "dokument_bearbeiten.html",
                dokument=dokument,
                kategorien=kategorien,
                werte=werte,
                heute=heute.isoformat(),
                fehler=fehler,
                bestaetigung=_bearbeitungs_bestaetigung.dumps(
                    {
                        "dokument_id": dokument_id,
                        "stand": stand,
                    }
                ),
            ),
            status,
        )

    def abweisen(meldung, status=400):
        db.session.rollback()
        return formular(meldung, status)

    if request.method == "GET":
        return formular()

    werte["firma"] = request.form.get("firma", "").strip()
    werte["kategorie_id"] = request.form.get("kategorie_id", "").strip()
    if dokument.ablagedatum is None:
        werte["ablagedatum"] = request.form.get("ablagedatum", "").strip()

    try:
        bestaetigung = _bearbeitungs_bestaetigung.loads(
            request.form.get("bestaetigung", ""), max_age=15 * 60
        )
    except (BadSignature, SignatureExpired):
        return abweisen(
            "Das Formular ist abgelaufen oder ungültig. Prüfe die Angaben "
            "und speichere sie erneut."
        )
    if (
        not isinstance(bestaetigung, dict)
        or bestaetigung.get("dokument_id") != dokument_id
    ):
        return abweisen("Die Bestätigung gehört nicht zu diesem Dokument.")
    if bestaetigung.get("stand") != stand:
        return abweisen(
            "Das Dokument wurde inzwischen geändert. Die aktuell gespeicherten "
            "Angaben kannst du über Abbrechen ansehen. Prüfe deine Eingaben "
            "vor einem erneuten Speichern.",
            409,
        )

    if not werte["firma"] or len(werte["firma"]) > 120:
        return abweisen("Bitte eine Firma mit 1 bis 120 Zeichen eingeben.")

    try:
        kategorie_id = int(werte["kategorie_id"]) if werte["kategorie_id"] else None
    except ValueError:
        return abweisen("Bitte eine gültige Kategorie auswählen.")
    kategoriename = "Dokument"
    if kategorie_id is not None:
        kategorie = next((k for k in kategorien if k.id == kategorie_id), None)
        if kategorie is None:
            return abweisen("Die ausgewählte Kategorie existiert nicht mehr.")
        kategoriename = kategorie.name

    try:
        ablagedatum = dokument.ablagedatum or date.fromisoformat(werte["ablagedatum"])
    except ValueError:
        return abweisen("Bitte das tatsächliche Ablagedatum ergänzen.")
    if ablagedatum > heute:
        return abweisen("Das Ablagedatum darf nicht in der Zukunft liegen.")

    endung = Path(dokument.dateiname).suffix.lower()
    if endung not in {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}:
        return abweisen("Das gespeicherte Dateiformat wird nicht unterstützt.")
    neuer_name = erstelle_dateinamen(ablagedatum, kategoriename, werte["firma"], endung)
    if len(neuer_name) > 255:
        return abweisen("Der erzeugte Dateiname ist zu lang.")

    try:
        ergebnis = db.session.execute(
            db.update(Dokument)
            .where(Dokument.id == dokument_id, Dokument.ist_entwurf.is_(False))
            .values(
                firma=werte["firma"],
                kategorie_id=kategorie_id,
                ablagedatum=ablagedatum,
                dateiname=neuer_name,
            )
        )
        if ergebnis.rowcount != 1:
            db.session.rollback()
            abort(404)
        db.session.commit()
    except IntegrityError:
        return abweisen(
            "Die Kategorie konnte nicht zugeordnet werden. Lade die Seite "
            "neu und wähle eine vorhandene Kategorie aus.",
            409,
        )
    except SQLAlchemyError:
        return abweisen(
            "Die Angaben konnten nicht gespeichert werden. Bitte versuche es erneut.",
            503,
        )
    return redirect(url_for("dokument_detail", dokument_id=dokument_id), code=303)
