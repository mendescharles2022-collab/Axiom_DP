from app.extensions import db


class CnaeSecundario(db.Model):
    __tablename__ = "cnaes_secundarios"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    codigo = db.Column(db.String(20))
    descricao = db.Column(db.String(300))

    def __repr__(self):
        return f"<CnaeSecundario {self.codigo} ({self.empresa_id})>"
