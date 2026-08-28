from app.extensions import db


class InscricaoEstadual(db.Model):
    __tablename__ = "inscricoes_estaduais"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    uf = db.Column(db.String(2))
    numero = db.Column(db.String(30))
    situacao = db.Column(db.String(100))

    def __repr__(self):
        return f"<InscricaoEstadual {self.uf}:{self.numero} ({self.empresa_id})>"
