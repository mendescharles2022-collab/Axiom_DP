from app.extensions import db


class Socio(db.Model):
    __tablename__ = "socios"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    nome = db.Column(db.String(200))
    qualificacao = db.Column(db.String(150))
    cpf_parcial = db.Column(db.String(20))  # a API só devolve o CPF mascarado do sócio

    def __repr__(self):
        return f"<Socio {self.nome} ({self.empresa_id})>"
