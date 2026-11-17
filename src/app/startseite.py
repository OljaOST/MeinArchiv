"""Daten und Ansichten für die Startseite und die Kategorieauswahl."""

from flask import abort, render_template, request
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from .datenbank import Dokument, Kategorie, db
from .dokumentordner import ordner_url


def kategorien_mit_anzahl():
    return db.session.execute(
        db.select(
            Kategorie.id,
            Kategorie.name,
            db.func.count(Dokument.id).label("anzahl"),
        )
        .outerjoin(
            Dokument,
            and_(
                Dokument.kategorie_id == Kategorie.id,
                Dokument.ist_entwurf.is_(False),
            ),
        )
        .group_by(Kategorie.id, Kategorie.name)
        .order_by(db.func.lower(Kategorie.name), Kategorie.id)
    ).all()


def startseite_anzeigen():
    gespeichert = request.args.get("gespeichert", type=int)
    if gespeichert is not None and not 0 < gespeichert <= 2_147_483_647:
        gespeichert = None
    try:
        kategorien = kategorien_mit_anzahl()

        dokumente = db.session.execute(
            db.select(
                Dokument.id,
                Dokument.dateiname,
                Dokument.ablagedatum,
                Dokument.kategorie_id,
                Kategorie.name.label("kategoriename"),
            )
            .outerjoin(Kategorie, Dokument.kategorie_id == Kategorie.id)
            .where(Dokument.ist_entwurf.is_(False))
            .order_by(
                Dokument.ablagedatum.desc().nulls_last(),
                Dokument.id.desc(),
            )
            .limit(5)
        ).all()

        anzahl = db.session.scalar(
            db.select(db.func.count(Dokument.id)).where(Dokument.ist_entwurf.is_(False))
        )
        if gespeichert and gespeichert not in {dokument.id for dokument in dokumente}:
            gespeichert = db.session.scalar(
                db.select(Dokument.id).where(
                    Dokument.id == gespeichert, Dokument.ist_entwurf.is_(False)
                )
            )
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "startseite.html",
                kategorien=[],
                dokumente=[],
                anzahl=None,
                ladefehler=True,
            ),
            503,
        )

    return render_template(
        "startseite.html",
        kategorien=kategorien,
        dokumente=dokumente,
        anzahl=anzahl,
        ladefehler=False,
        gespeichert=gespeichert,
    )


def kategorie_dokumente_anzeigen(kategorie_id):
    suche = request.args.get("q", "").strip()

    try:
        if kategorie_id is None:
            kategorie = {"id": None, "name": "Ohne Kategorie"}
        else:
            kategorie = db.session.get(Kategorie, kategorie_id)
            if kategorie is None:
                abort(404)

        abfrage = (
            db.select(
                Dokument.id,
                Dokument.dateiname,
                Dokument.ablagedatum,
            )
            .where(
                Dokument.kategorie_id == kategorie_id,
                Dokument.ist_entwurf.is_(False),
            )
            .order_by(
                Dokument.ablagedatum.desc().nulls_last(),
                Dokument.id.desc(),
            )
        )
        if suche:
            abfrage = abfrage.where(
                Dokument.dateiname.icontains(suche, autoescape=True)
            )
        dokumente = db.session.execute(abfrage).all()
    except SQLAlchemyError:
        db.session.rollback()
        return (
            render_template(
                "kategorie_dokumente.html",
                kategorie=None,
                dokumente=[],
                suche=suche,
                ladefehler=True,
            ),
            503,
        )

    return render_template(
        "kategorie_dokumente.html",
        kategorie=kategorie,
        ordner_url=ordner_url(kategorie_id),
        verschoben=request.args.get("verschoben", type=int),
        umbenannt=request.args.get("umbenannt", type=int),
        dokumente=dokumente,
        suche=suche,
        ladefehler=False,
    )
