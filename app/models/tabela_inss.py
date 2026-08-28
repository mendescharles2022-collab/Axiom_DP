import json

from app.extensions import db


class TabelaINSS(db.Model):
    """
    Tabela de contribuição previdenciária do empregado, histórica por
    vigência (HANDOFF seção 5.5) — o cálculo é progressivo por faixa
    (marginal), igual à regra vigente desde 03/2020, então faixas_json
    não guarda "parcela a deduzir": o motor de cálculo soma cada faixa.

    faixas_json: lista ordenada por "ate" crescente, ex.:
        [{"ate": 1412.00, "aliquota": 7.5}, {"ate": 2666.68, "aliquota": 9}, ...]
    """
    __tablename__ = "tabelas_inss"

    id = db.Column(db.Integer, primary_key=True)
    vigencia_inicio = db.Column(db.String(10), nullable=False)  # AAAA-MM-DD
    vigencia_fim = db.Column(db.String(10))  # NULL = vigente até segunda ordem
    faixas_json = db.Column(db.Text, nullable=False)
    teto_contribuicao = db.Column(db.Numeric(10, 2), nullable=False)

    def faixas(self):
        return json.loads(self.faixas_json)

    def __repr__(self):
        return f"<TabelaINSS {self.vigencia_inicio} a {self.vigencia_fim or '...'}>"
