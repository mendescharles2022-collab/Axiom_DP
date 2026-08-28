import pytest

from app.models.empresa import Empresa
from app.models.rubrica import Rubrica
from scripts.importar_dados_escritorio import (
    PLANILHA_EMPRESAS,
    PLANILHA_RUBRICAS,
    _formatar_documento,
    _somente_digitos,
    importar_empresas,
    importar_rubricas,
)


@pytest.mark.parametrize(
    "digitos,tipo,esperado",
    [
        ("39538135000140", "CNPJ", "39.538.135/0001-40"),
        ("438290151", "CPF", "004.382.901-51"),
        ("69932590100", "CPF", "699.325.901-00"),
    ],
)
def test_formatar_documento(digitos, tipo, esperado):
    assert _formatar_documento(digitos, tipo) == esperado


def test_somente_digitos():
    assert _somente_digitos("39.538.135/0001-40") == "39538135000140"
    assert _somente_digitos(39538135000140) == "39538135000140"
    assert _somente_digitos(None) == ""


def test_importar_empresas_da_planilha_real(app):
    with app.app_context():
        criadas, atualizadas, ignoradas = importar_empresas(PLANILHA_EMPRESAS)
        total = Empresa.query.count()
        cnpj = Empresa.query.filter_by(tipo_inscricao="CNPJ").count()
        cpf = Empresa.query.filter_by(tipo_inscricao="CPF").count()

    assert criadas + atualizadas == 537
    assert ignoradas == 0
    assert total == criadas
    # A planilha de origem tem um CNPJ repetido em duas linhas (mesma
    # empresa com razões sociais diferentes) — por isso 490, não 491.
    assert cnpj == 490
    assert cpf == 46


def test_importar_empresas_e_idempotente(app):
    with app.app_context():
        importar_empresas(PLANILHA_EMPRESAS)
        total_primeira_vez = Empresa.query.count()

        criadas, atualizadas, _ = importar_empresas(PLANILHA_EMPRESAS)
        total_segunda_vez = Empresa.query.count()

    assert criadas == 0
    assert total_primeira_vez == total_segunda_vez


def test_reimportar_nao_duplica_documento_com_zero_a_esquerda(app):
    """
    Regressão: uma empresa cujo documento (CNPJ ou CPF) tem zero à
    esquerda na planilha original (ex.: CPF "438290151", que vira
    "004.382.901-51") não pode virar um INSERT duplicado ao rodar a
    importação de novo — a chave de correspondência precisa considerar o
    zero à esquerda tanto no valor recém-lido quanto no já salvo.
    """
    with app.app_context():
        importar_empresas(PLANILHA_EMPRESAS)
        empresa = Empresa.query.filter_by(cnpj="004.382.901-51").first()
        assert empresa is not None

        importar_empresas(PLANILHA_EMPRESAS)  # não deve lançar IntegrityError
        assert Empresa.query.filter_by(cnpj="004.382.901-51").count() == 1


def test_importar_rubricas_da_planilha_real(app):
    with app.app_context():
        criadas, atualizadas = importar_rubricas(PLANILHA_RUBRICAS)
        total = Rubrica.query.count()
        tipos = {r.tipo for r in Rubrica.query.all()}

    assert criadas == 1798
    assert atualizadas == 0
    assert total == 1798
    assert tipos == {"P", "D", "I", "ID"}


def test_importar_rubricas_e_idempotente(app):
    with app.app_context():
        importar_rubricas(PLANILHA_RUBRICAS)
        criadas, atualizadas = importar_rubricas(PLANILHA_RUBRICAS)
        total = Rubrica.query.count()

    assert criadas == 0
    assert atualizadas == 1798
    assert total == 1798
