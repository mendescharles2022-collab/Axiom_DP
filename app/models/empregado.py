from datetime import datetime
from app.extensions import db


class Empregado(db.Model):
    __tablename__ = "empregados"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)

    # Dados pessoais
    nome_completo = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, index=True)
    rg = db.Column(db.String(20))
    data_nascimento = db.Column(db.String(10))
    nacionalidade = db.Column(db.String(50), default="brasileira")
    estado_civil = db.Column(db.String(30))
    ctps_numero = db.Column(db.String(20))
    ctps_serie = db.Column(db.String(10))
    pis_pasep = db.Column(db.String(20))
    endereco = db.Column(db.String(300))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(150))

    # Dados funcionais
    cargo = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    tipo_contrato = db.Column(
        db.String(30), default="indeterminado"
    )  # indeterminado, experiencia, determinado, tempo_parcial, intermitente, aprendiz, estagio
    data_admissao = db.Column(db.String(10))
    data_desligamento = db.Column(db.String(10))
    jornada_semanal_horas = db.Column(db.Float)
    salario_base = db.Column(db.Numeric(10, 2))

    # Dados bancários
    banco = db.Column(db.String(100))
    agencia = db.Column(db.String(20))
    conta = db.Column(db.String(30))
    chave_pix = db.Column(db.String(150))

    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documentos_emitidos = db.relationship(
        "DocumentoEmitido", backref="empregado", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "empresa_id": self.empresa_id,
            "nome_completo": self.nome_completo,
            "cpf": self.cpf,
            "cargo": self.cargo,
            "setor": self.setor,
            "tipo_contrato": self.tipo_contrato,
            "data_admissao": self.data_admissao,
            "salario_base": float(self.salario_base) if self.salario_base else None,
            "ativo": self.ativo,
        }

    def __repr__(self):
        return f"<Empregado {self.nome_completo} ({self.cpf})>"
