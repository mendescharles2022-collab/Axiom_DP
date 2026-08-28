"""
Semeia as tabelas fiscais históricas (TabelaINSS, TabelaIRRF,
TabelaIRRFRedutor) usadas pelo motor de cálculo de folha
(app/services/calculo_folha.py). Idempotente por vigencia_inicio: rodar
de novo não duplica.

Fonte dos valores: dataset oficial fornecido pelo Charles (histórico
consolidado INSS 2012-2026, IRRF 2015-2026 e o redutor da Lei
15.270/2025 a partir de 01/2026) — não é mais estimativa da memória de
treinamento como na primeira versão deste script.

*** ÚNICO PONTO AINDA NÃO CONFIRMADO PELA FONTE OFICIAL ***
A dedução por dependente do IRRF (R$ 189,59/mês) não veio no dataset
fornecido — é um valor que não muda há vários reajustes de tabela e por
isso foi mantido igual em todas as vigências abaixo, mas vale confirmar
com o Charles se ele tiver a fonte oficial à mão.

Uso: python scripts/seed_tabelas_fiscais.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.tabela_inss import TabelaINSS
from app.models.tabela_irrf import TabelaIRRF
from app.models.tabela_irrf_redutor import TabelaIRRFRedutor

DEDUCAO_DEPENDENTE_PADRAO = 189.59

# Cada item: (vigencia_inicio, vigencia_fim, teto_contribuicao, [(ate, aliquota), ...])
TABELAS_INSS = [
    ("2012-01-01", "2012-12-31", 3916.20, [(1174.86, 8), (1958.10, 9), (3916.20, 11)]),
    ("2013-01-01", "2013-12-31", 4159.00, [(1247.70, 8), (2079.50, 9), (4159.00, 11)]),
    ("2014-01-01", "2014-12-31", 4390.24, [(1317.07, 8), (2195.12, 9), (4390.24, 11)]),
    ("2015-01-01", "2015-12-31", 4663.75, [(1399.12, 8), (2331.88, 9), (4663.75, 11)]),
    ("2016-01-01", "2016-12-31", 5189.82, [(1556.94, 8), (2594.92, 9), (5189.82, 11)]),
    ("2017-01-01", "2017-12-31", 5531.31, [(1659.38, 8), (2765.66, 9), (5531.31, 11)]),
    ("2018-01-01", "2018-12-31", 5645.80, [(1693.72, 8), (2822.90, 9), (5645.80, 11)]),
    ("2019-01-01", "2019-12-31", 5839.45, [(1751.81, 8), (2919.72, 9), (5839.45, 11)]),
    ("2020-01-01", "2020-12-31", 6101.06, [(1045.00, 7.5), (2089.60, 9), (3134.40, 12), (6101.06, 14)]),
    ("2021-01-01", "2021-12-31", 6433.57, [(1100.00, 7.5), (2203.48, 9), (3305.22, 12), (6433.57, 14)]),
    ("2022-01-01", "2022-12-31", 7087.22, [(1212.00, 7.5), (2427.35, 9), (3641.03, 12), (7087.22, 14)]),
    ("2023-01-01", "2023-12-31", 7507.49, [(1320.00, 7.5), (2571.29, 9), (3856.94, 12), (7507.49, 14)]),
    ("2024-01-01", "2024-12-31", 7786.02, [(1412.00, 7.5), (2666.68, 9), (4000.03, 12), (7786.02, 14)]),
    ("2025-01-01", "2025-12-31", 8157.41, [(1518.00, 7.5), (2793.88, 9), (4190.83, 12), (8157.41, 14)]),
    ("2026-01-01", None, 8475.55, [(1621.00, 7.5), (2902.84, 9), (4354.27, 12), (8475.55, 14)]),
]

# Cada item: (vigencia_inicio, vigencia_fim, [(ate, aliquota, parcela_deduzir), ...])
# "ate": None na última faixa = sem limite superior.
TABELAS_IRRF = [
    ("2015-04-01", "2023-04-30", [
        (1903.98, 0, 0), (2826.65, 7.5, 142.80), (3751.05, 15, 354.80),
        (4664.68, 22.5, 636.13), (None, 27.5, 869.36),
    ]),
    ("2023-05-01", "2024-01-31", [
        (2112.00, 0, 0), (2826.65, 7.5, 158.40), (3751.05, 15, 370.40),
        (4664.68, 22.5, 651.73), (None, 27.5, 884.96),
    ]),
    ("2024-02-01", "2025-04-30", [
        (2259.20, 0, 0), (2826.65, 7.5, 169.44), (3751.05, 15, 381.44),
        (4664.68, 22.5, 662.77), (None, 27.5, 896.00),
    ]),
    ("2025-05-01", "2025-12-31", [
        (2428.80, 0, 0), (2826.65, 7.5, 182.16), (3751.05, 15, 394.16),
        (4664.68, 22.5, 675.49), (None, 27.5, 908.73),
    ]),
    # 2026-01 em diante: faixas idênticas às de 05/2025 (a mudança de
    # 01/2026 é o redutor da Lei 15.270/2025, aplicado depois da tabela
    # — ver TabelaIRRFRedutor, não uma tabela progressiva nova).
    ("2026-01-01", None, [
        (2428.80, 0, 0), (2826.65, 7.5, 182.16), (3751.05, 15, 394.16),
        (4664.68, 22.5, 675.49), (None, 27.5, 908.73),
    ]),
]


def _faixas_inss_json(faixas):
    return json.dumps([{"ate": ate, "aliquota": aliquota} for ate, aliquota in faixas])


def _faixas_irrf_json(faixas):
    return json.dumps(
        [{"ate": ate, "aliquota": aliquota, "parcela_deduzir": parcela} for ate, aliquota, parcela in faixas]
    )


def seed_inss():
    criadas = 0
    for vigencia_inicio, vigencia_fim, teto, faixas in TABELAS_INSS:
        if TabelaINSS.query.filter_by(vigencia_inicio=vigencia_inicio).first():
            continue
        db.session.add(
            TabelaINSS(
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=vigencia_fim,
                faixas_json=_faixas_inss_json(faixas),
                teto_contribuicao=teto,
            )
        )
        criadas += 1
    db.session.commit()
    print(f"TabelaINSS — {criadas} vigência(s) criada(s) de {len(TABELAS_INSS)}.")


def seed_irrf():
    criadas = 0
    for vigencia_inicio, vigencia_fim, faixas in TABELAS_IRRF:
        if TabelaIRRF.query.filter_by(vigencia_inicio=vigencia_inicio).first():
            continue
        db.session.add(
            TabelaIRRF(
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=vigencia_fim,
                faixas_json=_faixas_irrf_json(faixas),
                deducao_por_dependente=DEDUCAO_DEPENDENTE_PADRAO,
            )
        )
        criadas += 1
    db.session.commit()
    print(f"TabelaIRRF — {criadas} vigência(s) criada(s) de {len(TABELAS_IRRF)}.")


def seed_irrf_redutor():
    if TabelaIRRFRedutor.query.filter_by(vigencia_inicio="2026-01-01").first():
        print("TabelaIRRFRedutor 2026-01-01 já existe.")
        return
    db.session.add(
        TabelaIRRFRedutor(
            vigencia_inicio="2026-01-01",
            vigencia_fim=None,
            limite_isencao=5000.00,
            limite_redutor=7350.00,
            valor_base_formula=978.62,
            coeficiente_formula=0.133145,
        )
    )
    db.session.commit()
    print("TabelaIRRFRedutor 2026-01-01 criada.")


def main():
    app = create_app()
    with app.app_context():
        seed_inss()
        seed_irrf()
        seed_irrf_redutor()


if __name__ == "__main__":
    main()
