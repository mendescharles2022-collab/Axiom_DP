from app.extensions import db


class Rubrica(db.Model):
    """
    Catálogo global de rubricas de folha (não é por empresa) — importado de
    dados_para_importar/RELAÇÃO_DE_RUBRICA.xls (HANDOFF seção 5.5 e 7).

    Os campos incidencia_* guardam o código de incidência bruto da planilha
    de origem (não um booleano): o significado exato de cada código
    pertence ao motor de cálculo de folha (sprint AXDP-003.9), que ainda
    vai consumir esse catálogo — aqui só garantimos que o dado chegou
    intacto no banco.
    """
    __tablename__ = "rubricas"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.Integer, unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(2), nullable=False)  # P=provento, D=desconto, I=informativo, ID=informativo dedutível

    incidencia_irrf = db.Column(db.Integer)
    incidencia_inss = db.Column(db.Integer)
    incidencia_fgts = db.Column(db.Integer)
    incidencia_pis = db.Column(db.Integer)

    def __repr__(self):
        return f"<Rubrica {self.codigo} {self.nome}>"
