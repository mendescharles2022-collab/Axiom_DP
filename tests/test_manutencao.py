import pytest

from app import create_app
from app.extensions import db
from manutencao import create_manutencao_app


@pytest.fixture
def apps(tmp_path):
    """
    Sobe as duas apps Flask (porta principal e porta de manutenção)
    apontando para o MESMO arquivo SQLite — reproduz em teste o cenário
    real de dois processos separados compartilhando o banco em modo WAL.
    """
    db_path = tmp_path / "test.sqlite3"
    overrides = {
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    }
    principal = create_app(config_overrides=overrides)
    manutencao = create_manutencao_app(config_overrides=overrides)
    yield principal, manutencao
    with principal.app_context():
        db.session.remove()
        db.drop_all()


def _criar_usuario(app, login, senha, perfil, nome):
    from app.models.usuario import Usuario

    with app.app_context():
        usuario = Usuario(nome=nome, login=login, perfil=perfil, ativo=True)
        usuario.set_senha(senha)
        db.session.add(usuario)
        db.session.commit()
    return login, senha


def _ligar_manutencao(app, titulo="Em manutenção", mensagem="Voltamos já"):
    from app.models.configuracao_manutencao import ConfiguracaoManutencao

    with app.app_context():
        config = ConfiguracaoManutencao.obter()
        config.ativo = True
        config.titulo = titulo
        config.mensagem = mensagem
        db.session.commit()


def test_configuracao_manutencao_obter_cria_registro_padrao_inativo(apps):
    principal, _ = apps
    from app.models.configuracao_manutencao import ConfiguracaoManutencao

    with principal.app_context():
        config = ConfiguracaoManutencao.obter()
        assert config.id == 1
        assert config.ativo is False


def test_modo_manutencao_bloqueia_usuario_anonimo_na_porta_principal(apps):
    principal, _ = apps
    _ligar_manutencao(principal, titulo="Estamos atualizando")

    resposta = principal.test_client().get("/")
    assert resposta.status_code == 503
    assert "Estamos atualizando" in resposta.get_data(as_text=True)


def test_modo_manutencao_bloqueia_operador_na_porta_principal(apps):
    principal, _ = apps
    login, senha = _criar_usuario(principal, "operador", "senha1234", "operador", "Operador")
    _ligar_manutencao(principal)

    client = principal.test_client()
    client.post("/login", data={"login": login, "senha": senha})
    resposta = client.get("/")
    assert resposta.status_code == 503


def test_modo_manutencao_nao_bloqueia_admin_na_porta_principal(apps):
    principal, _ = apps
    login, senha = _criar_usuario(principal, "admin", "senha1234", "admin", "Admin")
    _ligar_manutencao(principal)

    client = principal.test_client()
    client.post("/login", data={"login": login, "senha": senha})
    resposta = client.get("/")
    assert resposta.status_code == 200


def test_login_continua_acessivel_durante_manutencao(apps):
    principal, _ = apps
    _criar_usuario(principal, "admin", "senha1234", "admin", "Admin")
    _ligar_manutencao(principal)

    resposta = principal.test_client().get("/login")
    assert resposta.status_code == 200


def test_manutencao_login_rejeita_usuario_nao_admin(apps):
    _, manutencao = apps
    login, senha = _criar_usuario(manutencao, "operador", "senha1234", "operador", "Operador")

    client = manutencao.test_client()
    resposta = client.post("/login", data={"login": login, "senha": senha})
    assert resposta.status_code == 401
    assert "administrador" in resposta.get_data(as_text=True).lower()


def test_manutencao_login_aceita_admin_e_mostra_painel(apps):
    _, manutencao = apps
    login, senha = _criar_usuario(manutencao, "admin", "senha1234", "admin", "Admin")

    client = manutencao.test_client()
    resposta = client.post("/login", data={"login": login, "senha": senha}, follow_redirects=True)
    assert resposta.status_code == 200
    assert "Modo manuten" in resposta.get_data(as_text=True)


def test_manutencao_painel_exige_login(apps):
    _, manutencao = apps
    resposta = manutencao.test_client().get("/")
    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_liga_manutencao_pela_porta_admin_bloqueia_porta_principal(apps):
    """
    Fluxo ponta a ponta que reproduz o cenário real: liga o modo
    manutenção pela porta de administração (5601) e confirma que a
    porta principal (5600) passa a bloquear usuários não-admin — as
    duas apps só se comunicam através do banco compartilhado.
    """
    principal, manutencao = apps
    login, senha = _criar_usuario(principal, "admin", "senha1234", "admin", "Admin")

    client_manutencao = manutencao.test_client()
    client_manutencao.post("/login", data={"login": login, "senha": senha})
    resposta = client_manutencao.post(
        "/",
        data={
            "ativo": "on",
            "titulo": "Atualizando o sistema",
            "mensagem": "Fazendo uma atualização, já volta.",
            "previsao_retorno": "",
        },
        follow_redirects=True,
    )
    assert resposta.status_code == 200

    client_principal_anonimo = principal.test_client()
    resposta_bloqueada = client_principal_anonimo.get("/")
    assert resposta_bloqueada.status_code == 503
    assert "Atualizando o sistema" in resposta_bloqueada.get_data(as_text=True)

    # e desligando de novo pela mesma porta, a principal volta ao normal
    client_manutencao.post(
        "/",
        data={"titulo": "Atualizando o sistema", "mensagem": "", "previsao_retorno": ""},
    )
    resposta_normal = principal.test_client().get("/")
    assert resposta_normal.status_code == 302  # sem manutenção, "/" exige login (redireciona), não 503
