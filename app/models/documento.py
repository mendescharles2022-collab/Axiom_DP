from app.extensions import db


class TemplateDocumento(db.Model):
    __tablename__ = "templates_documentos"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(100), nullable=False)  # ex.: "Avisos Prévios"
    nome = db.Column(db.String(200), nullable=False)  # ex.: "Aviso Prévio Indenizado"
    arquivo = db.Column(db.String(300), nullable=False)  # caminho relativo em docs_templates/
    descricao = db.Column(db.Text)
    variaveis_extra_json = db.Column(db.Text)  # JSON: [{"nome":..., "rotulo":..., "tipo":...}]
    ativo = db.Column(db.Boolean, default=True)

    documentos_emitidos = db.relationship(
        "DocumentoEmitido", backref="template", lazy=True
    )

    def campos_extra(self):
        import json
        if not self.variaveis_extra_json:
            return []
        return json.loads(self.variaveis_extra_json)

    def to_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "nome": self.nome,
            "arquivo": self.arquivo,
            "descricao": self.descricao,
            "campos_extra": self.campos_extra(),
        }

    def __repr__(self):
        return f"<TemplateDocumento {self.categoria} / {self.nome}>"
