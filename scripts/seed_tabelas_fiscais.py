"""
Semeia as tabelas fiscais históricas (TabelaINSS, TabelaIRRF,
TabelaIRRFRedutor) usadas pelo motor de cálculo de folha
(app/services/calculo_folha.py). Idempotente por vigencia_inicio: rodar
de novo não duplica.

*** ATENÇÃO — VALORES PRECISAM SER CONFERIDOS ANTES DE USO REAL ***

- TabelaINSS e TabelaIRRF abaixo são a tabela vigente a partir de
  02/2024 (Lei 14.663/2023) — a última que os dados de treinamento
  confirmam com boa confiança. Se já existir uma tabela mais recente
  (2025, 2026...) quando este projeto for usado para fechar folha real,
  ela precisa ser adicionada como uma NOVA linha (vigencia_inicio novo),
  nunca sobrescrevendo esta — é assim que o cálculo de competências
  passadas continua correto.
- TabelaIRRFRedutor (Lei nº 15.270/2025, a partir de 01/2026) usa os
  valores exatamente como descritos no HANDOFF_CLAUDE_CODE.md, seção 5.5
  (fornecidos pelo Charles/Klaus, não de memória de treinamento).

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

# INSS vigente a partir de 01/02/2024 (Portaria Interministerial MPS/MF nº 2/2024)
FAIXAS_INSS_2024 = [
    {"ate": 1412.00, "aliquota": 7.5},
    {"ate": 2666.68, "aliquota": 9},
    {"ate": 4000.03, "aliquota": 12},
    {"ate": 7786.02, "aliquota": 14},
]
TETO_INSS_2024 = 7786.02

# IRRF vigente a partir de 01/02/2024 (Lei nº 14.663/2023)
FAIXAS_IRRF_2024 = [
    {"ate": 2259.20, "aliquota": 0, "parcela_deduzir": 0},
    {"ate": 2826.65, "aliquota": 7.5, "parcela_deduzir": 169.44},
    {"ate": 3751.05, "aliquota": 15, "parcela_deduzir": 381.44},
    {"ate": 4664.68, "aliquota": 22.5, "parcela_deduzir": 662.77},
    {"ate": None, "aliquota": 27.5, "parcela_deduzir": 896.00},
]
DEDUCAO_DEPENDENTE_2024 = 189.59


def seed_inss():
    if TabelaINSS.query.filter_by(vigencia_inicio="2024-02-01").first():
        print("TabelaINSS 2024-02-01 já existe.")
        return
    db.session.add(
        TabelaINSS(
            vigencia_inicio="2024-02-01",
            vigencia_fim=None,
            faixas_json=json.dumps(FAIXAS_INSS_2024),
            teto_contribuicao=TETO_INSS_2024,
        )
    )
    db.session.commit()
    print("TabelaINSS 2024-02-01 criada.")


def seed_irrf():
    if TabelaIRRF.query.filter_by(vigencia_inicio="2024-02-01").first():
        print("TabelaIRRF 2024-02-01 já existe.")
        return
    db.session.add(
        TabelaIRRF(
            vigencia_inicio="2024-02-01",
            vigencia_fim=None,
            faixas_json=json.dumps(FAIXAS_IRRF_2024),
            deducao_por_dependente=DEDUCAO_DEPENDENTE_2024,
        )
    )
    db.session.commit()
    print("TabelaIRRF 2024-02-01 criada.")


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
