from app.extensions import db


class TemplateRecibo(db.Model):
    """
    Catálogo de modelos visuais de recibo avulso (contracheque/pró-labore)
    — HANDOFF ADENDO seção A. Cada modelo é um .docx com placeholders
    docxtpl em app/docs_templates_recibo/, gerado por
    scripts/gerar_templates_recibo.py.
    """
    __tablename__ = "templates_recibos"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # contracheque | pro_labore
    nome = db.Column(db.String(150), nullable=False)
    arquivo = db.Column(db.String(300), nullable=False)  # caminho relativo em docs_templates_recibo/
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<TemplateRecibo {self.tipo}/{self.nome}>"
