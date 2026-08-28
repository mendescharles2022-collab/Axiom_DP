from sqlalchemy import text

from app.extensions import db


def test_wal_mode_ativo(app):
    with app.app_context():
        modo = db.session.execute(text("PRAGMA journal_mode")).scalar()
        assert modo.lower() == "wal"
