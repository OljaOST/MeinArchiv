import os

import pytest

from app import app
from app.datenbank import db


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Keine separate Testdatenbank angegeben.",
)
def test_verbindung_zur_testdatenbank():
    with app.app_context():
        # Vor dem Datenbankzugriff die Verbindung prüfen.
        assert db.engine.url.host == "127.0.0.1"
        assert db.engine.url.port == 5433
        assert db.engine.url.database == "meinarchiv_test"

        datenbankname = db.session.execute(
            db.text("SELECT current_database()")
        ).scalar_one()

        assert datenbankname == "meinarchiv_test"