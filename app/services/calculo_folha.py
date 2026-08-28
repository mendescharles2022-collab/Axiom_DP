"""
Motor de cálculo de contracheque/pró-labore avulso (HANDOFF seção 5.5).

IMPORTANTE — leia antes de usar para fechar folha real:

1. As tabelas de INSS/IRRF ficam no banco (TabelaINSS/TabelaIRRF/
   TabelaIRRFRedutor), históricas por vigência — nunca hardcoded aqui, de
   propósito, para que competências passadas continuem corretas mesmo
   depois de uma tabela nova entrar em vigor. scripts/seed_tabelas_fiscais.py
   semeia o histórico completo (INSS 2012-2026, IRRF 2015-2026 e o
   redutor da Lei nº 15.270/2025 a partir de 01/2026) a partir de um
   dataset oficial fornecido pelo Charles — não são mais estimativas da
   memória de treinamento. Único valor ainda não confirmado pela fonte
   oficial: a dedução por dependente do IRRF (ver aviso no próprio
   script). Se uma tabela nova entrar em vigor, adicione uma linha nova
   (nunca edite/sobrescreva uma vigência existente).
2. `incidencia_irrf` em Rubrica usa os códigos oficiais da Tabela 21 do
   eSocial (leiaute S-1.3) — ver INCIDENCIAS_IRRF_QUE_NAO_ENTRAM_NA_BASE
   abaixo, classificado a partir da descrição oficial de cada código
   (fonte: Charles). `incidencia_inss`/`incidencia_fgts`/`incidencia_pis`
   AINDA usam a convenção simplificada "0 = não incide, qualquer outro
   código = incide" — o Charles ainda não forneceu a tabela oficial de
   incidências de INSS/FGTS/PIS do eSocial (equivalente à Tabela 21, mas
   para contribuição previdenciária/FGTS/PIS). Assim que ele mandar,
   troque essas duas pela mesma lógica de lookup usada para o IRRF.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.models.tabela_inss import TabelaINSS
from app.models.tabela_irrf import TabelaIRRF
from app.models.tabela_irrf_redutor import TabelaIRRFRedutor

DOIS_CENTAVOS = Decimal("0.01")
ALIQUOTA_FGTS = Decimal("8")

# Códigos da Tabela 21 do eSocial (incidência de IRRF) cuja natureza NÃO
# soma na base tributável mensal: rendimentos não tributáveis/isentos
# (aposentado 65+, diárias, ajuda de custo, indenizações, moléstia grave,
# abono pecuniário de férias, auxílio moradia, parcela isenta do
# transporte), o "desconto simplificado" (não é rendimento) e verbas que
# apenas transitam pela folha sem relação com IR (código 9) ou passam por
# depósito/compensação judicial. Qualquer código fora desta lista soma na
# base (inclusive códigos desconhecidos — mais seguro tributar de mais do
# que de menos).
INCIDENCIAS_IRRF_QUE_NAO_ENTRAM_NA_BASE = frozenset({
    0, 1, 9, 67, 68, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
    81, 82, 83, 700, 701, 9067, 9082, 9083,
})


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

    if tabela_redutor and base <= _d(tabela_redutor.limite_redutor):
        # Fórmula única e contínua em toda a faixa 0–limite_redutor (não é
        # "zera até limite_isencao, reduz parcial depois" — essa leitura
        # inicial estava errada). limite_isencao (R$ 5.000) é só o ponto
        # de referência que a lei usa para descrever o benefício ("redução
        # de até R$ 312,89 até R$ 5.000,00"): abaixo dele o valor da
        # fórmula quase sempre excede o imposto apurado (por isso zera na
        # prática), mas o cálculo real é sempre min(fórmula, imposto
        # apurado) — nunca gera crédito negativo.
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


def _incide_irrf(codigo) -> bool:
    """Lookup real, a partir da Tabela 21 do eSocial (ver topo do arquivo)."""
    if codigo is None:
        return False
    try:
        codigo_int = int(codigo)
    except (TypeError, ValueError):
        return True
    return codigo_int not in INCIDENCIAS_IRRF_QUE_NAO_ENTRAM_NA_BASE


def _incide_heuristica(codigo) -> bool:
    """
    Usada só para INSS/FGTS/PIS até o Charles enviar a tabela oficial de
    incidências equivalente à Tabela 21 do eSocial (ver aviso no topo).
    """
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
        if _incide_heuristica(rubrica.incidencia_inss):
            base_inss += valor_liquido_item
        if _incide_irrf(rubrica.incidencia_irrf):
            base_irrf_bruta += valor_liquido_item
        if _incide_heuristica(rubrica.incidencia_fgts):
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
