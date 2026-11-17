"""Dateinamenvorschlag und gemeinsame Speichervorschau für Uploads."""

import os
import re
import secrets
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import abort, jsonify, redirect, render_template, request, url_for
from itsdangerous import BadData, URLSafeTimedSerializer
from openai import APIError
from sqlalchemy.exc import SQLAlchemyError

from .dateinamen import dateiname_mit_endung, erstelle_dateinamen
from .datenbank import Dokument, Kategorie, db
from .dokumentansicht import dokument_vorschau_anzeigen
from .ki import erkenne_dokument

_formularcode = URLSafeTimedSerializer(
    os.getenv("FORMULAR_SCHLUESSEL") or secrets.token_urlsafe(32),
    salt="meinarchiv-import-speichern",
)
_ungueltige_zeichen = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def namensvorschlag_vorbereiten(dokument_id, inhalt, endung):
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return

    try:
        kategorien = {
            k.name: k.id
            for k in db.session.execute(db.select(Kategorie.id, Kategorie.name))
        }
        db.session.rollback()
        ergebnis = erkenne_dokument(inhalt, endung, list(kategorien))
        if not isinstance(ergebnis, dict):
            return
        kategorie = ergebnis.get("kategorie")
        firma = ergebnis.get("firma")
        if kategorie is not None and (
            not isinstance(kategorie, str) or kategorie not in kategorien
        ):
            return
        if not isinstance(firma, str) or not 1 <= len(firma.strip()) <= 120:
            return

        datum = datetime.now(ZoneInfo("Europe/Zurich")).date()
        firma = re.sub(r"[\x00-\x1f\x7f]", " ", firma).strip()
        firma = firma or "Unbekannt"
        name = erstelle_dateinamen(datum, kategorie or "Dokument", firma, endung)
        db.session.execute(
            db.update(Dokument)
            .where(
                Dokument.id == dokument_id,
                Dokument.ist_entwurf.is_(True),
                Dokument.ablagedatum.is_(None),
            )
            .values(
                dateiname=name,
                firma=firma,
                kategorie_id=kategorien.get(kategorie),
                ablagedatum=datum,
            )
        )
        db.session.commit()
    except (APIError, ValueError, SQLAlchemyError):
        # Der Upload ist bereits gesichert und kann mit seinem Namen weitergehen.
        db.session.rollback()


def import_vorschau(dokument_id):
    return dokument_vorschau_anzeigen(dokument_id, ist_entwurf=True)


def scan_entwurf_antwort(dokument_id):
    dokument = db.session.get(Dokument, dokument_id)
    if dokument is None or not dokument.ist_entwurf:
        abort(404)

    dateiname = dokument.dateiname
    if dokument.ablagedatum is None:
        datum = datetime.now(ZoneInfo("Europe/Zurich")).date()
        dateiname = erstelle_dateinamen(datum, "Dokument", "Unbekannt", ".pdf")

    return jsonify(
        stamm=Path(dateiname).stem,
        ki_erkannt=dokument.ablagedatum is not None,
        bestaetigung=_formularcode.dumps([dokument_id, "scan"]),
        speichern=url_for("entwurf_speichern", dokument_id=dokument_id, quelle="scan"),
        verwerfen=url_for("entwurf_verwerfen", dokument_id=dokument_id, quelle="scan"),
    )


def import_speichern(dokument_id):
    scan = request.args.get("quelle") == "scan"
    scan_post = (
        scan and request.method == "POST" and request.form.get("scan_editor") == "ja"
    )
    erwarteter_code = [dokument_id, "scan"] if scan_post else dokument_id
    try:
        abfrage = db.select(
            Dokument.id,
            Dokument.ist_entwurf,
            Dokument.dateiname,
            Dokument.ablagedatum,
        ).where(Dokument.id == dokument_id)
        if request.method == "POST":
            abfrage = abfrage.with_for_update()
        dokument = db.session.execute(abfrage).one_or_none()
        if dokument is None:
            abort(404)
        if not dokument.ist_entwurf:
            return redirect(url_for("dokument_detail", dokument_id=dokument_id), 303)

        endung = Path(dokument.dateiname).suffix
        stamm = _ungueltige_zeichen.sub("-", Path(dokument.dateiname).stem)
        stamm = stamm.strip(" .") or "Dokument"
        fehler = None
        if request.method == "POST":
            stamm = request.form.get("dateiname", "").strip()
            try:
                code = _formularcode.loads(
                    request.form.get("bestaetigung", ""), max_age=15 * 60
                )
            except BadData:
                code = None
            if code != erwarteter_code:
                fehler = (
                    "Das Formular ist abgelaufen. Prüfe den Namen und speichere erneut."
                )
            else:
                try:
                    dateiname = dateiname_mit_endung(stamm, endung)
                except ValueError as exc:
                    fehler = str(exc)
            aenderungen = {}
            if scan_post and fehler is None:
                pdf = request.files.get("dokument")
                inhalt = pdf.read() if pdf is not None else b""
                if endung.lower() != ".pdf" or not inhalt.startswith(b"%PDF-"):
                    fehler = "Das Scan-PDF konnte nicht gelesen werden."
                else:
                    aenderungen["inhalt"] = inhalt
            if fehler is None:
                db.session.execute(
                    db.update(Dokument)
                    .where(
                        Dokument.id == dokument_id,
                        Dokument.ist_entwurf.is_(True),
                    )
                    .values(
                        dateiname=dateiname,
                        ablagedatum=(
                            dokument.ablagedatum
                            or datetime.now(ZoneInfo("Europe/Zurich")).date()
                        ),
                        ist_entwurf=False,
                        **aenderungen,
                    )
                )
                db.session.commit()
                return redirect(url_for("index", gespeichert=dokument_id), 303)

        if scan_post:
            return jsonify(
                fehler=fehler,
                bestaetigung=_formularcode.dumps(erwarteter_code),
            ), 400

        return render_template(
            "import_speichern.html",
            dokument=dokument,
            stamm=stamm,
            endung=endung,
            bestaetigung=_formularcode.dumps(dokument_id),
            fehler=fehler,
            scan=scan,
        ), (400 if fehler else 200)
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "dokument_fehler.html",
                meldung=("Das Dokument konnte nicht geladen oder gespeichert werden."),
            ),
            503,
        )
