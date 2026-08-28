import json

from app.extensions import db


class TabelaIRRF(db.Model):
    """
    Tabela progressiva do IRRF, histórica por vigência (HANDOFF seção
    5.5). Ao contrário do INSS, o IRRF usa o método de "parcela a
    deduzir": imposto = base_calculo * aliquota_da_faixa - parcela_deduzir
    da faixa em que a base se encaixa (não é somado faixa a faixa).

    faixas_json: lista ordenada por "ate" crescente; a última faixa usa
    "ate": null para representar "sem limite superior", ex.:
        [{"ate": 2259.20, "aliquota": 0, "parcela_deduzir": 0},
         {"ate": 2826.65, "aliquota": 7.5, "parcela_deduzir": 169.44},
         ...,
         {"ate": null, "aliquota": 27.5, "parcela_deduzir": 896.00}]
    """
    __tablename__ = "tabelas_irrf"

    id = db.Column(db.Integer, primary_key=True)
    vigencia_inicio = db.Column(db.String(10), nullable=False)
    vigencia_fim = db.Column(db.String(10))
    faixas_json = db.Column(db.Text, nullable=False)
    deducao_por_dependente = db.Column(db.Numeric(10, 2), nullable=False)

    def faixas(self):
        return json.loads(self.faixas_json)

    def __repr__(self):
        return f"<TabelaIRRF {self.vigencia_inicio} a {self.vigencia_fim or '...'}>"
