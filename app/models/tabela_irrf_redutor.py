from app.extensions import db


class TabelaIRRFRedutor(db.Model):
    """
    Redutor adicional do IRRF a partir de 01/2026 (Lei nº 15.270/2025) —
    aplicado DEPOIS do cálculo pela tabela progressiva tradicional
    (TabelaIRRF), nunca a substituindo (HANDOFF seção 5.5):

    - Zera o imposto para rendimento tributável até `limite_isencao`.
    - Entre `limite_isencao` e `limite_redutor`, reduz o imposto apurado
      pela fórmula:
          redutor = valor_base - (coeficiente * rendimento_tributavel)
      limitado ao valor do imposto apurado pela tabela tradicional (nunca
      gera valor negativo/crédito).
    - Sem redução acima de `limite_redutor`.

    Também histórica por vigência: se a fórmula ou os limites mudarem em
    anos seguintes, uma nova linha é adicionada em vez de sobrescrever
    esta (mesma lógica de TabelaINSS/TabelaIRRF).
    """
    __tablename__ = "tabelas_irrf_redutor"

    id = db.Column(db.Integer, primary_key=True)
    vigencia_inicio = db.Column(db.String(10), nullable=False)
    vigencia_fim = db.Column(db.String(10))

    limite_isencao = db.Column(db.Numeric(10, 2), nullable=False)
    limite_redutor = db.Column(db.Numeric(10, 2), nullable=False)
    valor_base_formula = db.Column(db.Numeric(10, 6), nullable=False)
    coeficiente_formula = db.Column(db.Numeric(10, 6), nullable=False)

    def __repr__(self):
        return f"<TabelaIRRFRedutor {self.vigencia_inicio} a {self.vigencia_fim or '...'}>"
