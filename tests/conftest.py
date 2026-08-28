import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    application = create_app(
        config_overrides={
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
