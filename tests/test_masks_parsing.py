import pytest

from app.routes.paginas import _parse_valor_brl


@pytest.mark.parametrize(
    "texto,esperado",
    [
        ("", None),
        ("1.500,50", 1500.50),
        ("1.234.567,89", 1234567.89),
        ("500,00", 500.00),
        ("1500.50", 1500.50),  # fallback sem JS/máscara
        ("0,00", 0.0),
    ],
)
def test_parse_valor_brl(texto, esperado):
    assert _parse_valor_brl(texto) == esperado


def test_empregado_com_salario_formatado_pt_br(app, auth_client):
    from app.extensions import db
    from app.models.empresa import Empresa

    with app.app_context():
        empresa = Empresa(razao_social="Empresa Salario", cnpj="33.333.333/0001-33")
        db.session.add(empresa)
        db.session.commit()
        empresa_id = empresa.id

    resp = auth_client.post(
        f"/empresas/{empresa_id}/empregados/novo",
        data={"nome_completo": "Empregado Salario", "cpf": "222.222.222-22", "salario_base": "1.500,50"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        from app.models.empregado import Empregado

        empregado = Empregado.query.filter_by(nome_completo="Empregado Salario").first()
        assert float(empregado.salario_base) == 1500.50
