"""Archivstatus und lesender Export der abgelegten Dokumente."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

from flask import render_template, send_file
from sqlalchemy.exc import SQLAlchemyError

from .datenbank import Dokument, Kategorie, db


def einstellungen_anzeigen():
    statistik = None
    try:
        gruppen = db.session.execute(
            db.select(
                Dokument.ist_entwurf,
                db.func.count(Dokument.id).label("anzahl"),
                db.func.coalesce(db.func.sum(db.func.length(Dokument.inhalt)), 0).label(
                    "bytes"
                ),
            ).group_by(Dokument.ist_entwurf)
        ).all()
        abgelegt = next((g for g in gruppen if not g.ist_entwurf), None)
        entwuerfe = next((g for g in gruppen if g.ist_entwurf), None)
        statistik = {
            "dokumente": abgelegt.anzahl if abgelegt else 0,
            "entwuerfe": entwuerfe.anzahl if entwuerfe else 0,
            "bytes": abgelegt.bytes if abgelegt else 0,
            "kategorien": db.session.scalar(db.select(db.func.count(Kategorie.id))),
        }
    except SQLAlchemyError:
        db.session.rollback()

    return render_template(
        "einstellungen.html",
        statistik=statistik,
        ki_eingerichtet=bool(os.getenv("OPENAI_API_KEY", "").strip()),
    ), (200 if statistik is not None else 503)


def _export_dateiname(dateiname):
    # Keine Pfadteile aus einem gespeicherten Dateinamen übernehmen.
    name = PurePosixPath(dateiname.replace("\\", "/")).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "-", name).strip(" .")
    if not name:
        name = "Dokument"
    reserviert = {"CON", "PRN", "AUX", "NUL"}
    reserviert.update(f"COM{i}" for i in range(1, 10))
    reserviert.update(f"LPT{i}" for i in range(1, 10))
    if name.split(".", 1)[0].upper() in reserviert:
        name = "_" + name
    return name


def dokumente_exportieren():
    zeitpunkt = datetime.now(ZoneInfo("Europe/Zurich"))
    export = {
        "format": "MeinArchiv-Dokumentexport",
        "version": 1,
        "exportiert_am": zeitpunkt.isoformat(timespec="seconds"),
        "kategorien": [],
        "anzahl_dokumente": 0,
        "dokumente": [],
    }
    datei = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    ergebnis = None
    try:
        export["kategorien"] = [
            {"id": k.id, "name": k.name}
            for k in db.session.execute(
                db.select(Kategorie.id, Kategorie.name).order_by(Kategorie.id)
            ).all()
        ]
        ergebnis = db.session.execute(
            db.select(
                Dokument.id,
                Dokument.dateiname,
                Dokument.firma,
                Dokument.ablagedatum,
                Dokument.kategorie_id,
                Dokument.inhalt,
                Kategorie.name.label("kategoriename"),
            )
            .outerjoin(Kategorie, Dokument.kategorie_id == Kategorie.id)
            .where(Dokument.ist_entwurf.is_(False))
            .order_by(Dokument.id)
            .execution_options(yield_per=1)
        )
        with ZipFile(datei, "w", compression=ZIP_DEFLATED, compresslevel=3) as archiv:
            for dokument in ergebnis:
                pfad = (
                    f"dokumente/{dokument.id}/{_export_dateiname(dokument.dateiname)}"
                )
                archiv.writestr(pfad, dokument.inhalt)
                export["dokumente"].append(
                    {
                        "id": dokument.id,
                        "dateiname": dokument.dateiname,
                        "firma": dokument.firma,
                        "ablagedatum": (
                            dokument.ablagedatum.isoformat()
                            if dokument.ablagedatum
                            else None
                        ),
                        "kategorie_id": dokument.kategorie_id,
                        "kategorie": dokument.kategoriename,
                        "archivpfad": pfad,
                        "groesse_bytes": len(dokument.inhalt),
                        "sha256": hashlib.sha256(dokument.inhalt).hexdigest(),
                    }
                )
            export["anzahl_dokumente"] = len(export["dokumente"])
            archiv.writestr(
                "metadaten.json",
                json.dumps(export, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            archiv.writestr(
                "LIESMICH.txt",
                "MeinArchiv-Dokumentexport\n\n"
                "Die abgelegten Dateien liegen unter dokumente/<ID>/<Dateiname>.\n"
                "Jedes Dokument besitzt einen eigenen Ordner; "
                "gleiche Namen bleiben erhalten.\n"
                "metadaten.json enthält die Angaben und SHA-256-Prüfsummen.\n"
                "Offene Uploadentwürfe sind nicht enthalten.\n"
                "Der Export verändert keine Daten im Archiv.\n"
                "Dies ist ein Dokumentexport, kein vollständiges Datenbank-Backup.\n"
                "Eine automatische Wiederherstellung in MeinArchiv "
                "ist nicht enthalten.\n",
            )
        ergebnis.close()
        ergebnis = None
        # Die Lese-Transaktion vor dem Übertragen der ZIP-Datei beenden.
        db.session.rollback()
        datei.seek(0)
        antwort = send_file(
            datei,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"MeinArchiv-Export-{zeitpunkt:%Y%m%d-%H%M%S}.zip",
            max_age=0,
        )
        antwort.headers["Cache-Control"] = "no-store"
        antwort.headers["X-Content-Type-Options"] = "nosniff"
        antwort.call_on_close(datei.close)
        return antwort
    except (SQLAlchemyError, OSError):
        if ergebnis is not None:
            ergebnis.close()
            ergebnis = None
        db.session.rollback()
        datei.close()
        return render_template("export_fehler.html"), 503
    except Exception:
        if ergebnis is not None:
            ergebnis.close()
        datei.close()
        raise
