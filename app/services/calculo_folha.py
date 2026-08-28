"""
Motor de cálculo de contracheque/pró-labore avulso (HANDOFF seção 5.5).

IMPORTANTE — leia antes de usar para fechar folha real:

1. As tabelas de INSS/IRRF ficam no banco (TabelaINSS/TabelaIRRF/
   TabelaIRRFRedutor), históricas por vigência — nunca hardcoded aqui, de
   propósito, para que competências passadas continuem corretas mesmo
   depois de uma tabela nova entrar em vigor. O script
   scripts/seed_tabelas_fiscais.py semeia a tabela de fev/2024 (INSS e
   IRRF) e o redutor de 2026 (Lei nº 15.270/2025, valores dados
   diretamente pelo HANDOFF) — CONFIRME com o Charles/fonte oficial se
   essas são as tabelas vigentes na competência que você vai fechar antes
   de confiar no resultado; se não forem, adicione uma nova linha na
   tabela correspondente (não edite a antiga).
2. `incidencia_irrf`/`incidencia_inss`/`incidencia_fgts`/`incidencia_pis`
   em Rubrica guardam o código bruto da planilha `RELAÇÃO_DE_RUBRICA.xls`
   fornecida pelo escritório — o significado exato de cada código (ex.:
   11 vs. 12 vs. 21) não foi documentado para este projeto, só os valores
   brutos. Este motor assume a convenção mais simples e defensável
   observada nos dados: **0 = não incide, qualquer outro código = incide**
   (todo código de incidência aparece como 0 quando a rubrica claramente
   não afeta aquele tributo). CONFIRME esta convenção com o Charles — o
   sistema de origem da planilha pode ter uma tabela de códigos própria
   com nuances que essa regra simplificada não captura — antes de usar os
   totais para fechamento oficial.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.models.tabela_inss import TabelaINSS
from app.models.tabela_irrf import TabelaIRRF
from app.models.tabela_irrf_redutor import TabelaIRRFRedutor

DOIS_CENTAVOS = Decimal("0.01")
ALIQUOTA_FGTS = Decimal("8")


class CalculoFolhaError(Exception):
    pass


def _d(valor) -> Decimal:
    if valor is None:
        return Decimal("0")
    return Decimal(str(valor))


def _arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(DOIS_CENTAVOS, rounding=ROUND_HALF_UP)


def _tabela_vigente(modelo, competencia: str):
    """
    competencia: "AAAA-MM". Compara com o 1º dia do mês — vigencia_inicio
    e vigencia_fim são strings "AAAA-MM-DD", então a comparação léxica já
    equivale à cronológica.
    """
    data_ref = f"{competencia}-01"
    tabela = (
        modelo.query.filter(modelo.vigencia_inicio <= data_ref)
        .filter((modelo.vigencia_fim.is_(None)) | (modelo.vigencia_fim >= data_ref))
        .order_by(modelo.vigencia_inicio.desc())
        .first()
    )
    if not tabela:
        raise CalculoFolhaError(
            f"Nenhuma {modelo.__name__} vigente para a competência {competencia}."
        )
    return tabela


def calcular_inss(base_calculo, competencia: str) -> dict:
    """Cálculo progressivo (marginal) por faixa — regra vigente desde 03/2020."""
    tabela = _tabela_vigente(TabelaINSS, competencia)
    base = min(_d(base_calculo), _d(tabela.teto_contribuicao))

    total = Decimal("0")
    piso = Decimal("0")
    for faixa in tabela.faixas():
        teto_faixa = _d(faixa["ate"])
        limite = min(teto_faixa, base)
        if limite > piso:
            total += (limite - piso) * _d(faixa["aliquota"]) / Decimal("100")
        piso = teto_faixa
        if base <= teto_faixa:
            break

    return {"valor": _arredondar(total), "base": _arredondar(base), "tabela": tabela}


def calcular_irrf(base_calculo, competencia: str, dependentes: int = 0) -> dict:
    """
    base_calculo: rendimento tributável já líquido de INSS (a dedução por
    dependente é aplicada aqui, dentro desta função).
    """
    tabela = _tabela_vigente(TabelaIRRF, competencia)
    base = _d(base_calculo) - (_d(tabela.deducao_por_dependente) * (dependentes or 0))
    base = max(base, Decimal("0"))

    faixas = tabela.faixas()
    faixa_aplicavel = faixas[-1]
    for faixa in faixas:
        if faixa["ate"] is None or base <= _d(faixa["ate"]):
            faixa_aplicavel = faixa
            break

    valor_tabela = base * _d(faixa_aplicavel["aliquota"]) / Decimal("100") - _d(
        faixa_aplicavel["parcela_deduzir"]
    )
    valor_tabela = max(valor_tabela, Decimal("0"))

    redutor_valor = Decimal("0")
    tabela_redutor = None
    try:
        tabela_redutor = _tabela_vigente(TabelaIRRFRedutor, competencia)
    except CalculoFolhaError:
        tabela_redutor = None

    if tabela_redutor:
        if base <= _d(tabela_redutor.limite_isencao):
            redutor_valor = valor_tabela
        elif base <= _d(tabela_redutor.limite_redutor):
            redutor_bruto = _d(tabela_redutor.valor_base_formula) - (
                _d(tabela_redutor.coeficiente_formula) * base
            )
            redutor_valor = min(max(redutor_bruto, Decimal("0")), valor_tabela)

    valor_final = valor_tabela - redutor_valor
    return {
        "base": _arredondar(base),
        "valor_tabela": _arredondar(valor_tabela),
        "valor_redutor": _arredondar(redutor_valor),
        "valor_final": _arredondar(valor_final),
        "aliquota_faixa": _d(faixa_aplicavel["aliquota"]),
        "tabela": tabela,
        "tabela_redutor": tabela_redutor,
    }


def _incide(codigo) -> bool:
    return codigo not in (None, 0)


def montar_calculo_recibo(recibo, dependentes: int = 0) -> dict:
    """
    Percorre os itens de um ReciboAvulso, apura as bases de INSS/IRRF/FGTS
    a partir da incidência de cada Rubrica, calcula os tributos e devolve
    o líquido. Não persiste nada — quem chama decide o que fazer com o
    resultado (ex.: gerar o documento do recibo).
    """
    total_proventos = Decimal("0")
    total_descontos = Decimal("0")
    base_inss = Decimal("0")
    base_irrf_bruta = Decimal("0")
    base_fgts = Decimal("0")

    for item in recibo.itens:
        provento = _d(item.valor_provento)
        desconto = _d(item.valor_desconto)
        total_proventos += provento
        total_descontos += desconto

        valor_liquido_item = provento - desconto
        rubrica = item.rubrica
        if _incide(rubrica.incidencia_inss):
            base_inss += valor_liquido_item
        if _incide(rubrica.incidencia_irrf):
            base_irrf_bruta += valor_liquido_item
        if _incide(rubrica.incidencia_fgts):
            base_fgts += valor_liquido_item

    inss = calcular_inss(base_inss, recibo.competencia)

    base_irrf_apos_inss = max(base_irrf_bruta - inss["valor"], Decimal("0"))
    irrf = calcular_irrf(base_irrf_apos_inss, recibo.competencia, dependentes=dependentes)

    fgts_valor = _arredondar(max(base_fgts, Decimal("0")) * ALIQUOTA_FGTS / Decimal("100"))

    liquido = total_proventos - total_descontos - inss["valor"] - irrf["valor_final"]

    return {
        "total_proventos": _arredondar(total_proventos),
        "total_descontos": _arredondar(total_descontos),
        "base_inss": _arredondar(base_inss),
        "inss": inss,
        "base_irrf": _arredondar(base_irrf_apos_inss),
        "irrf": irrf,
        "base_fgts": _arredondar(base_fgts),
        "fgts": fgts_valor,
        "liquido": _arredondar(liquido),
    }
