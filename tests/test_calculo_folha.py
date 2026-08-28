from decimal import Decimal

import pytest

from app.extensions import db
from app.models.tabela_inss import TabelaINSS
from app.models.tabela_irrf import TabelaIRRF
from app.models.tabela_irrf_redutor import TabelaIRRFRedutor
from app.services.calculo_folha import (
    CalculoFolhaError,
    calcular_inss,
    calcular_irrf,
    montar_calculo_recibo,
)


@pytest.fixture
def tabelas_2024(app):
    with app.app_context():
        from scripts.seed_tabelas_fiscais import seed_inss, seed_irrf, seed_irrf_redutor

        seed_inss()
        seed_irrf()
        seed_irrf_redutor()
        yield


def test_calcular_inss_progressivo(app, tabelas_2024):
    with app.app_context():
        assert calcular_inss("3000", "2024-06")["valor"] == Decimal("258.82")
        assert calcular_inss("500", "2024-06")["valor"] == Decimal("37.50")
        assert calcular_inss("1412.00", "2024-06")["valor"] == Decimal("105.90")


def test_calcular_inss_respeita_teto(app, tabelas_2024):
    with app.app_context():
        resultado = calcular_inss("50000", "2024-06")
        assert resultado["valor"] == Decimal("908.86")
        assert resultado["base"] == Decimal("7786.02")


def test_calcular_inss_sem_tabela_vigente_lanca_erro(app, tabelas_2024):
    with app.app_context():
        with pytest.raises(CalculoFolhaError):
            calcular_inss("3000", "2005-01")  # antes da tabela mais antiga semeada (2012-01)


def test_calcular_irrf_isento(app, tabelas_2024):
    with app.app_context():
        assert calcular_irrf("2000", "2024-06")["valor_final"] == Decimal("0.00")


def test_calcular_irrf_faixas_intermediarias(app, tabelas_2024):
    with app.app_context():
        assert calcular_irrf("2500", "2024-06")["valor_final"] == Decimal("18.06")
        assert calcular_irrf("3000", "2024-06")["valor_final"] == Decimal("68.56")


def test_calcular_irrf_deducao_por_dependente(app, tabelas_2024):
    with app.app_context():
        sem_dependente = calcular_irrf("3000", "2024-06")["valor_final"]
        com_dependente = calcular_irrf("3000", "2024-06", dependentes=1)["valor_final"]
        assert com_dependente < sem_dependente


def test_redutor_2026_zera_ate_5000(app, tabelas_2024):
    with app.app_context():
        # Sem o redutor (2024), R$ 4.000 gera imposto normalmente.
        antes = calcular_irrf("4000", "2024-06")
        assert antes["valor_final"] > 0

        # Com o redutor vigente (2026+), o mesmo valor é zerado.
        depois = calcular_irrf("4000", "2026-03")
        assert depois["valor_final"] == Decimal("0.00")
        assert depois["valor_redutor"] == depois["valor_tabela"]


def test_redutor_2026_reduz_parcialmente_entre_5000_e_7350(app, tabelas_2024):
    with app.app_context():
        # Tabela de 01/2026: faixa 27,5% com parcela a deduzir R$ 908,73
        # (idêntica à de 05/2025 — 6000*0.275 - 908.73 = 741.27).
        resultado = calcular_irrf("6000", "2026-03")
        assert resultado["valor_tabela"] == Decimal("741.27")
        assert resultado["valor_redutor"] == Decimal("179.75")
        assert resultado["valor_final"] == Decimal("561.52")


def test_redutor_2026_nao_reduz_acima_de_7350(app, tabelas_2024):
    with app.app_context():
        resultado = calcular_irrf("8000", "2026-03")
        assert resultado["valor_redutor"] == Decimal("0.00")


def test_redutor_e_formula_continua_nao_zera_tudo_ate_exatamente_5000(app, tabelas_2024):
    """
    Regressão: a primeira versão deste motor tratava "até R$ 5.000" como
    zerar o imposto por completo (branch separado). A fórmula oficial é
    contínua: redutor = min(978,62 - 0,133145*base, imposto_apurado) em
    toda a faixa 0-7.350, então há uma faixa estreita ABAIXO de R$ 5.000
    (por volta de R$ 4.620 a R$ 5.000) onde a fórmula já é menor que o
    imposto apurado, sobrando um resíduo pequeno a pagar.
    """
    with app.app_context():
        resultado = calcular_irrf("5000", "2026-03")
        assert resultado["valor_final"] > Decimal("0.00")
        assert resultado["valor_final"] == Decimal("153.38")


def test_redutor_nunca_gera_credito_negativo(app, tabelas_2024):
    with app.app_context():
        # Base bem baixa (mas tributável) — o redutor não pode deixar o
        # imposto negativo mesmo que a fórmula bruta desse mais que o
        # imposto apurado.
        resultado = calcular_irrf("2300", "2026-03")
        assert resultado["valor_final"] >= Decimal("0.00")


def test_incidencia_irrf_usa_tabela_esocial_nao_binaria(app):
    from app.services.calculo_folha import _incide_irrf

    # Remuneração mensal normal -> soma na base do IRRF
    assert _incide_irrf(11) is True
    assert _incide_irrf(31) is True
    assert _incide_irrf(41) is True
    # Isenções da Tabela 21 do eSocial (não binário: são códigos != 0
    # mas ainda assim não entram na base, ao contrário da heurística
    # "0 = não incide, resto incide" usada para INSS/FGTS/PIS)
    assert _incide_irrf(72) is False  # Diárias
    assert _incide_irrf(74) is False  # Indenização/rescisão
    assert _incide_irrf(75) is False  # Abono pecuniário de férias
    assert _incide_irrf(701) is False  # Parte não tributável do transporte
    assert _incide_irrf(9) is False  # Verba sem relação com IR (passthrough)
    assert _incide_irrf(0) is False
    assert _incide_irrf(None) is False


def test_montar_calculo_recibo_nao_soma_rubrica_isenta_de_irrf_na_base(app, tabelas_2024):
    """
    Regressão: um item com incidencia_irrf=72 (Diárias, isento) não pode
    entrar na base do IRRF mesmo tendo código != 0 — a heurística antiga
    (0 = não incide, resto incide) erraria esse caso.
    """
    from app.models.empresa import Empresa
    from app.models.empregado import Empregado
    from app.models.rubrica import Rubrica
    from app.models.recibo_avulso import ReciboAvulso, ReciboAvulsoItem

    with app.app_context():
        empresa = Empresa(razao_social="Empresa Diarias LTDA", cnpj="77.777.777/0001-77")
        db.session.add(empresa)
        db.session.commit()

        rubrica_diarias = Rubrica(
            codigo=9, nome="DIARIAS DE VIAGEM", tipo="P",
            incidencia_irrf=72, incidencia_inss=0, incidencia_fgts=0, incidencia_pis=0,
        )
        db.session.add(rubrica_diarias)
        db.session.commit()

        recibo = ReciboAvulso(empresa_id=empresa.id, competencia="2024-06", tipo="pro_labore", nome_pro_labore="Teste")
        db.session.add(recibo)
        db.session.commit()
        db.session.add(ReciboAvulsoItem(recibo_id=recibo.id, rubrica_id=rubrica_diarias.id, valor_provento="500.00"))
        db.session.commit()

        resultado = montar_calculo_recibo(recibo)

    assert resultado["base_irrf"] == Decimal("0.00")


def test_montar_calculo_recibo(app, tabelas_2024):
    from app.models.empresa import Empresa
    from app.models.empregado import Empregado
    from app.models.rubrica import Rubrica
    from app.models.recibo_avulso import ReciboAvulso, ReciboAvulsoItem

    with app.app_context():
        empresa = Empresa(razao_social="Empresa Folha LTDA", cnpj="55.555.555/0001-55")
        db.session.add(empresa)
        db.session.commit()
        empregado = Empregado(empresa_id=empresa.id, nome_completo="Trabalhador Teste", cpf="999.999.999-99")
        db.session.add(empregado)

        rubrica_salario = Rubrica(
            codigo=1, nome="SALARIO BASE", tipo="P",
            incidencia_irrf=11, incidencia_inss=11, incidencia_fgts=11, incidencia_pis=11,
        )
        rubrica_vt = Rubrica(
            codigo=2, nome="VALE TRANSPORTE DESCONTO", tipo="D",
            incidencia_irrf=0, incidencia_inss=0, incidencia_fgts=0, incidencia_pis=0,
        )
        db.session.add_all([rubrica_salario, rubrica_vt])
        db.session.commit()

        recibo = ReciboAvulso(
            empresa_id=empresa.id, empregado_id=empregado.id,
            competencia="2024-06", tipo="contracheque",
        )
        db.session.add(recibo)
        db.session.commit()

        db.session.add_all([
            ReciboAvulsoItem(recibo_id=recibo.id, rubrica_id=rubrica_salario.id, valor_provento="3000.00"),
            ReciboAvulsoItem(recibo_id=recibo.id, rubrica_id=rubrica_vt.id, valor_desconto="180.00"),
        ])
        db.session.commit()

        resultado = montar_calculo_recibo(recibo)

    assert resultado["total_proventos"] == Decimal("3000.00")
    assert resultado["total_descontos"] == Decimal("180.00")
    assert resultado["base_inss"] == Decimal("3000.00")  # VT não incide, então não entra na base
    assert resultado["inss"]["valor"] == Decimal("258.82")
    assert resultado["base_fgts"] == Decimal("3000.00")
    assert resultado["fgts"] == Decimal("240.00")
    # líquido = proventos - descontos - inss - irrf
    assert resultado["liquido"] == Decimal("3000.00") - Decimal("180.00") - resultado["inss"]["valor"] - resultado["irrf"]["valor_final"]
