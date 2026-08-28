from app.extensions import db


class TabelaIRRFRedutor(db.Model):
    """
    Redutor adicional do IRRF a partir de 01/2026 (Lei nº 15.270/2025) —
    aplicado DEPOIS do cálculo pela tabela progressiva tradicional
    (TabelaIRRF), nunca a substituindo (HANDOFF seção 5.5).

    A fórmula é ÚNICA E CONTÍNUA em toda a faixa 0–`limite_redutor`:

        redutor = min(valor_base_formula - coeficiente_formula * base, imposto_apurado)

    limitada a nunca gerar valor negativo/crédito, e sem redução acima de
    `limite_redutor`. `limite_isencao` (R$ 5.000) NÃO é um ponto de corte
    no cálculo — é só o valor de referência que a lei usa para descrever
    o benefício ("redução de até R$ 312,89 para quem ganha até R$
    5.000"): abaixo dele a fórmula costuma superar o imposto apurado (por
    isso o imposto acaba zerado na prática para a maior parte dessa
    faixa), mas não há uma regra separada de "zera tudo abaixo de
    R$ 5.000" — é sempre a mesma fórmula, capada pelo imposto devido.

    Também histórica por vigência: se a fórmula ou os limites mudarem em
    anos seguintes, uma nova linha é adicionada em vez de sobrescrever
    esta (mesma lógica de TabelaINSS/TabelaIRRF).
    """
    __tablename__ = "tabelas_irrf_redutor"

    id = db.Column(db.Integer, primary_key=True)
    vigencia_inicio = db.Column(db.String(10), nullable=False)
    vigencia_fim = db.Column(db.String(10))

    limite_isencao = db.Column(db.Numeric(10, 2), nullable=False)  # referência informativa (ver docstring)
    limite_redutor = db.Column(db.Numeric(10, 2), nullable=False)
    valor_base_formula = db.Column(db.Numeric(10, 6), nullable=False)
    coeficiente_formula = db.Column(db.Numeric(10, 6), nullable=False)

    def __repr__(self):
        return f"<TabelaIRRFRedutor {self.vigencia_inicio} a {self.vigencia_fim or '...'}>"
