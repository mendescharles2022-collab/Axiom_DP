from datetime import datetime
from app.extensions import db
from app.utils.texto import titulo_pt


class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    # "cnpj" guarda o número de inscrição principal — CNPJ ou CPF, conforme
    # tipo_inscricao (produtor rural, autônomo e empregador doméstico usam
    # CPF). Mantido com este nome por compatibilidade com os 48 modelos de
    # documento já publicados, que referenciam {{ empresa.cnpj }}.
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    tipo_inscricao = db.Column(db.String(4), nullable=False, default="CNPJ")  # CNPJ | CPF
    cnpj = db.Column(db.String(18), unique=True, nullable=False, index=True)
    inscricao_estadual = db.Column(db.String(30))
    caepf = db.Column(db.String(20))
    cei = db.Column(db.String(20))
    cno = db.Column(db.String(20))

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
    data_fundacao = db.Column(db.String(10))
    porte = db.Column(db.String(100))
    capital_social = db.Column(db.Numeric(14, 2))
    situacao_especial = db.Column(db.String(150))
    data_situacao_especial = db.Column(db.String(10))
    telefone_rfb = db.Column(db.String(20))
    email_rfb = db.Column(db.String(150))
    opcao_simples = db.Column(db.Boolean)
    data_opcao_simples = db.Column(db.String(10))
    opcao_mei = db.Column(db.Boolean)
    data_opcao_mei = db.Column(db.String(10))
    ultima_consulta_api = db.Column(db.DateTime)

    # Dados do escritório (planilha de clientes)
    status = db.Column(db.String(20), default="Ativo")  # Ativo | Inativo (cliente do escritório)
    forma_envio = db.Column(db.String(100))

    # Recibo avulso / folha
    frase_quitacao_padrao_id = db.Column(db.Integer, db.ForeignKey("frases_quitacao.id"))

    # Metadados internos
    ativo = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empregados = db.relationship(
        "Empregado", backref="empresa", cascade="all, delete-orphan", lazy=True
    )
    cnaes_secundarios = db.relationship(
        "CnaeSecundario", backref="empresa", cascade="all, delete-orphan", lazy=True
    )
    socios = db.relationship(
        "Socio", backref="empresa", cascade="all, delete-orphan", lazy=True
    )
    inscricoes_estaduais = db.relationship(
        "InscricaoEstadual", backref="empresa", cascade="all, delete-orphan", lazy=True
    )
    frase_quitacao_padrao = db.relationship("FraseQuitacao")

    def endereco_completo(self):
        """
        Monta o endereço já com a capitalização corrigida (dados de
        logradouro/bairro/município costumam vir em CAIXA ALTA da RFB e das
        planilhas do escritório) — o dado bruto continua intacto nas
        colunas individuais.
        """
        partes = [
            titulo_pt(self.logradouro), self.numero,
            titulo_pt(self.complemento), titulo_pt(self.bairro),
        ]
        rua = ", ".join([p for p in partes if p])
        cidade = f"{titulo_pt(self.municipio)}/{self.uf}" if self.municipio else ""
        cep = f"CEP {self.cep}" if self.cep else ""
        return " - ".join([bloco for bloco in [rua, cidade, cep] if bloco])

    def to_dict(self):
        return {
            "id": self.id,
            "razao_social": self.razao_social,
            "nome_fantasia": self.nome_fantasia,
            "tipo_inscricao": self.tipo_inscricao,
            "cnpj": self.cnpj,
            "inscricao_estadual": self.inscricao_estadual,
            "caepf": self.caepf,
            "cei": self.cei,
            "cno": self.cno,
            "endereco": self.endereco_completo(),
            "cnae_principal": self.cnae_principal,
            "situacao_cadastral": self.situacao_cadastral,
            "porte": self.porte,
            "capital_social": float(self.capital_social) if self.capital_social is not None else None,
            "situacao_especial": self.situacao_especial,
            "opcao_simples": self.opcao_simples,
            "opcao_mei": self.opcao_mei,
            "status": self.status,
            "ativo": self.ativo,
        }

    def __repr__(self):
        return f"<Empresa {self.razao_social} ({self.cnpj})>"
