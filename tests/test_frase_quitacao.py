from app.extensions import db
from app.models.frase_quitacao import FraseQuitacao


def test_admin_cria_frase_quitacao(auth_client):
    resp = auth_client.post(
        "/frases-quitacao/nova",
        data={"nome": "Cliente X", "texto": "Frase obrigatória do cliente X."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Cliente X" in resp.get_data(as_text=True)


def test_operador_nao_gerencia_frases(client, operador_credenciais):
    login, senha = operador_credenciais
    client.post("/login", data={"login": login, "senha": senha})
    resp = client.get("/frases-quitacao/")
    assert resp.status_code == 403


def test_editar_frase_quitacao(app, auth_client):
    with app.app_context():
        frase = FraseQuitacao(nome="Original", texto="Texto original.")
        db.session.add(frase)
        db.session.commit()
        frase_id = frase.id

    resp = auth_client.post(
        f"/frases-quitacao/{frase_id}/editar",
        data={"nome": "Editada", "texto": "Texto editado."},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        frase = FraseQuitacao.query.get(frase_id)
        assert frase.nome == "Editada"


def test_excluir_frase_quitacao(app, auth_client):
    with app.app_context():
        frase = FraseQuitacao(nome="Para Excluir", texto="Texto.")
        db.session.add(frase)
        db.session.commit()
        frase_id = frase.id

    resp = auth_client.post(f"/frases-quitacao/{frase_id}/excluir", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert FraseQuitacao.query.get(frase_id) is None


def test_seed_frase_tradicional(app):
    with app.app_context():
        from scripts.seed_frase_quitacao import seed, TEXTO_TRADICIONAL

        seed()
        seed()  # idempotente
        frases = FraseQuitacao.query.filter_by(nome="Tradicional").all()
        assert len(frases) == 1
        assert frases[0].texto == TEXTO_TRADICIONAL
