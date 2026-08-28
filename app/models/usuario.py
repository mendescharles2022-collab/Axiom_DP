from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db

PERFIS_VALIDOS = ("admin", "operador")


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="operador")  # admin | operador
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime)

    def set_senha(self, senha_texto: str):
        self.senha_hash = generate_password_hash(senha_texto)

    def checar_senha(self, senha_texto: str) -> bool:
        return check_password_hash(self.senha_hash, senha_texto)

    @property
    def is_active(self):
        return self.ativo

    @property
    def is_admin(self):
        return self.perfil == "admin"

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<Usuario {self.login} ({self.perfil})>"
