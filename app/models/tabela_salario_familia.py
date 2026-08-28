import json

from app.extensions import db


class TabelaSalarioFamilia(db.Model):
    """
    Tabela do salário-família, histórica por vigência (mesmo padrão de
    TabelaINSS/TabelaIRRF). Paga ao empregado CLT cuja remuneração mensal
    fica dentro do limite, por dependente elegível (filho/equiparado até
    14 anos incompletos, ou inválido de qualquer idade) — HANDOFF ADENDO.

    faixas_json: lista ordenada por "limite_remuneracao" crescente. A
    maioria das vigências recentes (2020+) tem uma faixa só; vigências
    anteriores a 2020 tinham duas (extinta pela reforma da previdência,
    EC 103/2019). O valor da cota usado é o da primeira faixa cujo limite
    for >= à remuneração do empregado; remuneração acima do maior limite
    não tem direito ao benefício.
        [{"limite_remuneracao": 1980.38, "valor_cota": 67.54}]
    """
    __tablename__ = "tabelas_salario_familia"

    id = db.Column(db.Integer, primary_key=True)
    vigencia_inicio = db.Column(db.String(10), nullable=False)
    vigencia_fim = db.Column(db.String(10))
    faixas_json = db.Column(db.Text, nullable=False)

    def faixas(self):
        return json.loads(self.faixas_json)

    def __repr__(self):
        return f"<TabelaSalarioFamilia {self.vigencia_inicio} a {self.vigencia_fim or '...'}>"
