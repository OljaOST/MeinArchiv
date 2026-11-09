from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import false

db = SQLAlchemy()


class Kategorie(db.Model):
    __tablename__ = "kategorien"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)


class Dokument(db.Model):
    __tablename__ = "dokumente"

    id = db.Column(db.Integer, primary_key=True)
    dateiname = db.Column(db.String(255), nullable=False)
    inhalt = db.Column(db.LargeBinary, nullable=False)

    firma = db.Column(db.String(120), nullable=True)
    ablagedatum = db.Column(db.Date, nullable=True)

    kategorie_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "kategorien.id",
            name="fk_dokumente_kategorie_id_kategorien",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    kategorie = db.relationship("Kategorie")
    ist_entwurf = db.Column(
        db.Boolean,
        nullable=False,
        server_default=false(),
    )