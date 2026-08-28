import json
import os

from app.config import DOCS_TEMPLATES_DIR
from app.extensions import db
from app.models.documento import TemplateDocumento


def _seed_templates():
    with open(os.path.join(DOCS_TEMPLATES_DIR, "catalogo.json"), encoding="utf-8") as f:
        catalogo = json.load(f)
    for item in catalogo:
        db.session.add(
            TemplateDocumento(
                categoria=item["categoria"],
                nome=item["nome"].strip().title(),
                arquivo=item["arquivo"],
                variaveis_extra_json=json.dumps(item["campos_extras"], ensure_ascii=False),
            )
        )
    db.session.commit()


def test_catalogo_tem_48_modelos():
    with open(os.path.join(DOCS_TEMPLATES_DIR, "catalogo.json"), encoding="utf-8") as f:
        catalogo = json.load(f)
    assert len(catalogo) == 48


def test_dashboard_carrega(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_crud_empresa(client):
    resp = client.post(
        "/empresas/nova",
        data={"razao_social": "Empresa Teste LTDA", "cnpj": "11.222.333/0001-81"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Empresa Teste LTDA" in resp.get_data(as_text=True)


def test_crud_empregado(app, client):
    with app.app_context():
        from app.models.empresa import Empresa

        empresa = Empresa(razao_social="Empresa X", cnpj="00.000.000/0001-00")
        db.session.add(empresa)
        db.session.commit()
        empresa_id = empresa.id

    resp = client.post(
        f"/empresas/{empresa_id}/empregados/novo",
        data={"nome_completo": "Fulano de Tal", "cpf": "123.456.789-00"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Fulano de Tal" in resp.get_data(as_text=True)


def test_geracao_de_documento_via_http(app, client):
    with app.app_context():
        from app.models.empresa import Empresa
        from app.models.empregado import Empregado

        _seed_templates()
        empresa = Empresa(razao_social="Empresa Doc LTDA", cnpj="11.111.111/0001-11")
        db.session.add(empresa)
        db.session.commit()
        empregado = Empregado(
            empresa_id=empresa.id, nome_completo="Ciclano da Silva", cpf="987.654.321-00"
        )
        db.session.add(empregado)
        db.session.commit()

        template = TemplateDocumento.query.first()
        empresa_id, empregado_id, template_id = empresa.id, empregado.id, template.id

    resp = client.post(
        f"/empresas/{empresa_id}/emitir/{template_id}",
        data={"empregado_id": str(empregado_id)},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "gerado com sucesso" in resp.get_data(as_text=True)


def test_todos_os_48_modelos_geram_documento(app, client):
    with app.app_context():
        from app.models.empresa import Empresa
        from app.models.empregado import Empregado

        _seed_templates()
        empresa = Empresa(razao_social="Empresa Full LTDA", cnpj="22.222.222/0001-22")
        db.session.add(empresa)
        db.session.commit()
        empregado = Empregado(
            empresa_id=empresa.id, nome_completo="Beltrano Souza", cpf="111.111.111-11"
        )
        db.session.add(empregado)
        db.session.commit()

        empresa_id, empregado_id = empresa.id, empregado.id
        template_ids = [t.id for t in TemplateDocumento.query.all()]

    assert len(template_ids) == 48
    for template_id in template_ids:
        resp = client.post(
            f"/empresas/{empresa_id}/emitir/{template_id}",
            data={"empregado_id": str(empregado_id)},
            follow_redirects=True,
        )
        assert resp.status_code == 200, f"template {template_id} falhou"
        assert "Erro ao gerar" not in resp.get_data(as_text=True)
