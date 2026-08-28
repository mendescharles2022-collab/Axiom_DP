from datetime import datetime
from app.extensions import db


class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    cnpj = db.Column(db.String(18), unique=True, nullable=False, index=True)
    inscricao_estadual = db.Column(db.String(30))

    # Endereço
    logradouro = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    municipio = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    cep = db.Column(db.String(10))

    # Dados obtidos via API (cache local, evita bater na API toda hora)
    cnae_principal = db.Column(db.String(200))
    situacao_cadastral = db.Column(db.String(50))
    data_abertura = db.Column(db.String(10))
    natureza_juridica = db.Column(db.String(150))
    ultima_consulta_api = db.Column(db.DateTime)

    # Metadados internos
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empregados = db.relationship(
        "Empregado", backref="empresa", cascade="all, delete-orphan", lazy=True
    )

    def endereco_completo(self):
        partes = [self.logradouro, self.numero, self.complemento, self.bairro]
        rua = ", ".join([p for p in partes if p])
        cidade = f"{self.municipio}/{self.uf}" if self.municipio else ""
        return f"{rua} - {cidade} - CEP {self.cep or ''}".strip(" -")

    def to_dict(self):
        return {
            "id": self.id,
            "razao_social": self.razao_social,
            "nome_fantasia": self.nome_fantasia,
            "cnpj": self.cnpj,
            "inscricao_estadual": self.inscricao_estadual,
            "endereco": self.endereco_completo(),
            "cnae_principal": self.cnae_principal,
            "situacao_cadastral": self.situacao_cadastral,
            "ativo": self.ativo,
        }

    def __repr__(self):
        return f"<Empresa {self.razao_social} ({self.cnpj})>"
