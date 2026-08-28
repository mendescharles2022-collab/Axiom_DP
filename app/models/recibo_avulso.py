from datetime import datetime

from app.extensions import db


class ReciboAvulso(db.Model):
    """
    Contracheque ou recibo de pró-labore avulso (HANDOFF seção 5.5-5.6).
    "Avulso" porque o Axiom_DP não controla ponto/folha de pagamento
    completa — o escritório lança os itens de cada recibo manualmente e o
    motor de cálculo (app/services/calculo_folha.py) apura INSS/IRRF/FGTS.
    """
    __tablename__ = "recibos_avulsos"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    empregado_id = db.Column(db.Integer, db.ForeignKey("empregados.id"))  # nulo = pró-labore de sócio sem registro
    competencia = db.Column(db.String(7), nullable=False)  # "AAAA-MM"
    tipo = db.Column(db.String(20), nullable=False, default="contracheque")  # contracheque | pro_labore
    frase_quitacao_id = db.Column(db.Integer, db.ForeignKey("frases_quitacao.id"))
    template_recibo_id = db.Column(db.Integer, db.ForeignKey("templates_recibos.id"))
    nome_pro_labore = db.Column(db.String(200))  # nome do sócio, só quando empregado_id é nulo
    caminho_arquivo_gerado = db.Column(db.String(400))
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship("Empresa")
    empregado = db.relationship("Empregado")
    frase_quitacao = db.relationship("FraseQuitacao")
    template_recibo = db.relationship("TemplateRecibo")
    itens = db.relationship(
        "ReciboAvulsoItem", backref="recibo", cascade="all, delete-orphan", lazy=True,
        order_by="ReciboAvulsoItem.id",
    )

    def __repr__(self):
        return f"<ReciboAvulso {self.tipo} {self.competencia} empresa={self.empresa_id}>"


class ReciboAvulsoItem(db.Model):
    __tablename__ = "recibos_avulsos_itens"

    id = db.Column(db.Integer, primary_key=True)
    recibo_id = db.Column(db.Integer, db.ForeignKey("recibos_avulsos.id"), nullable=False)
    rubrica_id = db.Column(db.Integer, db.ForeignKey("rubricas.id"), nullable=False)
    referencia = db.Column(db.String(20))  # ex.: "30" (dias), "1" (mês), "50%"
    valor_provento = db.Column(db.Numeric(10, 2))
    valor_desconto = db.Column(db.Numeric(10, 2))

    rubrica = db.relationship("Rubrica")

    def __repr__(self):
        return f"<ReciboAvulsoItem rubrica={self.rubrica_id} recibo={self.recibo_id}>"
