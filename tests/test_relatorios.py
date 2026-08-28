import json

from app.extensions import db
from app.models.documento import TemplateDocumento
from app.models.empresa import Empresa
from app.models.empregado import Empregado
from app.models.emissao import DocumentoEmitido
from app.models.recibo_avulso import ReciboAvulso, ReciboAvulsoItem
from app.models.rubrica import Rubrica


def _seed_dados(app):
    with app.app_context():
        empresa_a = Empresa(razao_social="Empresa A LTDA", cnpj="10.000.000/0001-00")
        empresa_b = Empresa(razao_social="Empresa B LTDA", cnpj="20.000.000/0001-00")
        db.session.add_all([empresa_a, empresa_b])
        db.session.commit()

        template = TemplateDocumento(
            categoria="Declarações", nome="Declaração Teste", arquivo="dummy.docx",
            variaveis_extra_json=json.dumps([]),
        )
        db.session.add(template)
        db.session.commit()

        doc_a = DocumentoEmitido(
            template_id=template.id, empresa_id=empresa_a.id,
            caminho_arquivo_gerado="/tmp/doc_a.docx",
        )
        doc_b = DocumentoEmitido(
            template_id=template.id, empresa_id=empresa_b.id,
            caminho_arquivo_gerado="/tmp/doc_b.docx",
        )
        db.session.add_all([doc_a, doc_b])

        rubrica = Rubrica(codigo=1, nome="SALARIO", tipo="P",
                           incidencia_irrf=0, incidencia_inss=0, incidencia_fgts=0, incidencia_pis=0)
        db.session.add(rubrica)
        db.session.commit()

        recibo_a = ReciboAvulso(empresa_id=empresa_a.id, competencia="2024-06", tipo="pro_labore", nome_pro_labore="Socio A")
        db.session.add(recibo_a)
        db.session.commit()
        db.session.add(ReciboAvulsoItem(recibo_id=recibo_a.id, rubrica_id=rubrica.id, valor_provento="1000.00"))
        db.session.commit()

        return empresa_a.id, empresa_b.id


def test_relatorio_lista_documentos_e_recibos(app, auth_client):
    empresa_a_id, empresa_b_id = _seed_dados(app)

    resp = auth_client.get("/relatorios")
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert "Empresa A LTDA" in corpo
    assert "Empresa B LTDA" in corpo
    assert "Socio A" in corpo


def test_relatorio_filtra_por_empresa(app, auth_client):
    empresa_a_id, empresa_b_id = _seed_dados(app)

    resp = auth_client.get(f"/relatorios?empresa_id={empresa_a_id}")
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert "Declaração Teste" in corpo
    # "Empresa B LTDA" só pode aparecer no <select> de filtro, não numa linha de dados
    assert corpo.count("Empresa B LTDA") == 1


def test_relatorio_filtra_por_tipo(app, auth_client):
    _seed_dados(app)

    resp = auth_client.get("/relatorios?tipo=recibos")
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert "Documentos emitidos" not in corpo
    assert "Recibos avulsos" in corpo


def test_relatorio_filtra_por_periodo_fora_do_intervalo(app, auth_client):
    _seed_dados(app)

    resp = auth_client.get("/relatorios?data_inicio=2000-01-01&data_fim=2000-01-31")
    assert resp.status_code == 200
    corpo = resp.get_data(as_text=True)
    assert "Nenhum documento emitido no período." in corpo
    assert "Nenhum recibo avulso emitido no período." in corpo


def test_relatorio_exige_login(client):
    resp = client.get("/relatorios", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path in ("/login", "/primeiro-acesso")
