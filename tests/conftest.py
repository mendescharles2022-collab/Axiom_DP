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


def _criar_usuario(app, login="admin", senha="senha1234", perfil="admin", nome="Admin Teste"):
    from app.models.usuario import Usuario

    with app.app_context():
        usuario = Usuario(nome=nome, login=login, perfil=perfil, ativo=True)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
    return login, senha


@pytest.fixture
def admin_credenciais(app):
    return _criar_usuario(app, login="admin", perfil="admin")


@pytest.fixture
def operador_credenciais(app):
    return _criar_usuario(app, login="operador", perfil="operador", nome="Operador Teste")


@pytest.fixture
def auth_client(app, client, admin_credenciais):
    login, senha = admin_credenciais
    client.post("/login", data={"login": login, "senha": senha})
    return client
