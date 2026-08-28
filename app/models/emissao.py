from datetime import datetime
from app.extensions import db


class DocumentoEmitido(db.Model):
    __tablename__ = "documentos_emitidos"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("templates_documentos.id"), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    empregado_id = db.Column(db.Integer, db.ForeignKey("empregados.id"), nullable=True)

    caminho_arquivo_gerado = db.Column(db.String(400))
    dados_utilizados_json = db.Column(db.Text)  # snapshot do contexto usado no merge
    observacao = db.Column(db.Text)
    emitido_em = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship("Empresa")

    def __repr__(self):
        return f"<DocumentoEmitido template={self.template_id} empresa={self.empresa_id}>"
