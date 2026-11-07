from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Dokument(db.Model):
    __tablename__ = "dokumente"

    id = db.Column(db.Integer, primary_key=True)
    dateiname = db.Column(db.String(255), nullable=False)
    inhalt = db.Column(db.LargeBinary, nullable=False)