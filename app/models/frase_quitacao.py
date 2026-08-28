from app.extensions import db


class FraseQuitacao(db.Model):
    """
    Frases de quitação parametrizáveis para o recibo avulso (HANDOFF
    seção 5.6) — cada empresa pode ter uma frase padrão, e cada recibo
    emitido referencia qual frase foi usada.
    """
    __tablename__ = "frases_quitacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    texto = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<FraseQuitacao {self.nome}>"
