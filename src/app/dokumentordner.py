"""Ordnerwechsel für abgelegte Dokumente."""

import os
import secrets
from pathlib import Path

from flask import abort, redirect, render_template, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .dateinamen import dateiname_mit_endung
from .datenbank import Dokument, Kategorie, db

_formularcode = URLSafeTimedSerializer(
    os.getenv("FORMULAR_SCHLUESSEL") or secrets.token_urlsafe(32),
    salt="meinarchiv-ordnerwechsel",
)


def ordner_url(kategorie_id, **werte):
    if kategorie_id is None:
        return url_for("dokumente_ohne_kategorie", **werte)
    return url_for("kategorie_dokumente", kategorie_id=kategorie_id, **werte)


def dokument_verschieben_anzeigen(dokument_id):
    try:
        abfrage = db.select(Dokument.dateiname, Dokument.kategorie_id).where(
            Dokument.id == dokument_id, Dokument.ist_entwurf.is_(False)
        )
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
        auswahl = {"": None, **{str(k.id): k.id for k in kategorien}}
        ziel = str(dokument.kategorie_id or "")
        fehler = None
        status = 200
        if request.method == "POST":
            ziel = request.form.get("ziel", "")
            try:
                bestaetigung = _formularcode.loads(
                    request.form.get("bestaetigung", ""), max_age=15 * 60
                )
            except BadData:
                bestaetigung = None
            if bestaetigung != [dokument_id, dokument.kategorie_id]:
                fehler = "Prüfe den aktuellen Ordner und wähle das Ziel erneut."
                status = 409
            elif "ziel" not in request.form or ziel not in auswahl:
                fehler = "Wähle einen vorhandenen Zielordner."
                status = 400
            else:
                ziel_id = auswahl[ziel]
                if ziel_id == dokument.kategorie_id:
                    return redirect(ordner_url(ziel_id), code=303)
                db.session.execute(
                    db.update(Dokument)
                    .where(Dokument.id == dokument_id)
                    .values(kategorie_id=ziel_id)
                )
                db.session.commit()
                return redirect(ordner_url(ziel_id, verschoben=dokument_id), code=303)

        return (
            render_template(
                "dokument_verschieben.html",
                dokument=dokument,
                kategorien=kategorien,
                ziel=ziel,
                zurueck=ordner_url(dokument.kategorie_id),
                bestaetigung=_formularcode.dumps([dokument_id, dokument.kategorie_id]),
                fehler=fehler,
            ),
            status,
        )
    except IntegrityError:
        db.session.rollback()
        return (
            render_template(
                "dokument_fehler.html",
                meldung="Der Zielordner ist nicht mehr verfügbar.",
            ),
            409,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "dokument_fehler.html",
                meldung="Das Dokument konnte momentan nicht verschoben werden.",
            ),
            503,
        )


def dokument_umbenennen_anzeigen(dokument_id):
    try:
        abfrage = db.select(Dokument.dateiname, Dokument.kategorie_id).where(
            Dokument.id == dokument_id, Dokument.ist_entwurf.is_(False)
        )
        if request.method == "POST":
            abfrage = abfrage.with_for_update()
        dokument = db.session.execute(abfrage).one_or_none()
        if dokument is None:
            abort(404)

        endung = Path(dokument.dateiname).suffix
        name = dokument.dateiname
        formularstand = ["umbenennen", dokument_id, dokument.dateiname]
        fehler = None
        status = 200
        if request.method == "POST":
            name = request.form.get("dateiname", "")
            try:
                code = _formularcode.loads(
                    request.form.get("bestaetigung", ""), max_age=15 * 60
                )
            except BadData:
                code = None
            if code != formularstand:
                fehler = "Prüfe den aktuellen Dateinamen und speichere erneut."
                status = 409
            else:
                try:
                    dateiname = dateiname_mit_endung(name, endung)
                except ValueError as exc:
                    fehler = str(exc)
                    status = 400
                else:
                    db.session.execute(
                        db.update(Dokument)
                        .where(Dokument.id == dokument_id)
                        .values(dateiname=dateiname)
                    )
                    db.session.commit()
                    return redirect(
                        ordner_url(dokument.kategorie_id, umbenannt=dokument_id), 303
                    )
        return (
            render_template(
                "dokument_umbenennen.html",
                dokument=dokument,
                name=name,
                zurueck=ordner_url(dokument.kategorie_id),
                bestaetigung=_formularcode.dumps(formularstand),
                fehler=fehler,
            ),
            status,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "dokument_fehler.html",
                meldung="Das Dokument konnte momentan nicht umbenannt werden.",
            ),
            503,
        )
