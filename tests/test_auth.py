def test_rota_protegida_redireciona_para_login_quando_nao_autenticado(client):
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path in ("/login", "/primeiro-acesso")


def test_rota_protegida_redireciona_para_login_com_usuario_existente(client, admin_credenciais):
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == "/login"
    assert "Entrar" in resp.get_data(as_text=True)


def test_api_protegida_devolve_401_json_quando_nao_autenticado(client):
    resp = client.get("/api/empresas/")
    assert resp.status_code == 401
    assert resp.get_json()["erro"]


def test_primeiro_acesso_cria_admin_e_permite_login(client):
    resp = client.get("/login", follow_redirects=True)
    assert "primeiro" in resp.request.path or "acesso" in resp.request.path

    resp = client.post(
        "/primeiro-acesso",
        data={
            "nome": "Charles",
            "login": "charles",
            "senha": "senhaforte123",
            "confirmar_senha": "senhaforte123",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    resp = client.post(
        "/login", data={"login": "charles", "senha": "senhaforte123"}, follow_redirects=True
    )
    assert resp.status_code == 200
    assert "Charles" in resp.get_data(as_text=True)


def test_login_com_senha_errada_falha(client, admin_credenciais):
    login, _senha = admin_credenciais
    resp = client.post("/login", data={"login": login, "senha": "errada"})
    assert resp.status_code == 401


def test_usuario_inativo_nao_consegue_logar(app, client, admin_credenciais):
    from app.extensions import db
    from app.models.usuario import Usuario

    login, senha = admin_credenciais
    with app.app_context():
        usuario = Usuario.query.filter_by(login=login).first()
        usuario.ativo = False
        db.session.commit()

    resp = client.post("/login", data={"login": login, "senha": senha})
    assert resp.status_code == 401


def test_operador_nao_acessa_gestao_de_usuarios(client, operador_credenciais):
    login, senha = operador_credenciais
    client.post("/login", data={"login": login, "senha": senha})
    resp = client.get("/usuarios/")
    assert resp.status_code == 403


def test_admin_acessa_gestao_de_usuarios(auth_client):
    resp = auth_client.get("/usuarios/")
    assert resp.status_code == 200


def test_admin_cria_novo_usuario(auth_client):
    resp = auth_client.post(
        "/usuarios/novo",
        data={"nome": "Novo Operador", "login": "novo_op", "perfil": "operador", "senha": "outrasenha1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Novo Operador" in resp.get_data(as_text=True)


def test_logout_encerra_sessao(auth_client):
    resp = auth_client.post("/logout", follow_redirects=True)
    assert resp.status_code == 200
    resp2 = auth_client.get("/api/empresas/")
    assert resp2.status_code == 401
