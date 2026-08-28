"""
Axiom_DP — porta de administração/manutenção (processo separado).

App Flask mínimo, independente do restante do sistema, com uma função
só: ligar/desligar o modo manutenção da porta principal e editar
título, mensagem e previsão de retorno (`ConfiguracaoManutencao`).
Compartilha o banco de dados com a porta principal (SQLite em modo
WAL já suporta múltiplos processos lendo e gravando ao mesmo tempo —
ver app/extensions.py), mas não depende de nenhum outro módulo da
aplicação além do modelo e do login de administrador.

Fica de pé mesmo se a porta principal cair ou for reiniciada durante
uma atualização — ver main.py, que sobe as duas via um único comando
mas como processos do sistema operacional desacoplados um do outro
(HANDOFF_CLAUDE_CODE.md, adendo B).
"""
import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

from app.config import Config
from app.extensions import db
from app.models.configuracao_manutencao import ConfiguracaoManutencao
from app.models.usuario import Usuario

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = "0.0.0.0"
PORT = int(os.environ.get("AXIOM_DP_PORT_MANUTENCAO", "5601"))

# LoginManager próprio (não o de app.extensions) — este é um segundo app
# Flask, independente do principal, e não deve compartilhar login_view
# nem user_loader com ele.
login_manager_manutencao = LoginManager()


def create_manutencao_app(config_overrides: dict | None = None) -> Flask:
    Config.ensure_dirs()

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "app", "templates"),
        static_folder=os.path.join(BASE_DIR, "app", "static"),
    )
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    login_manager_manutencao.init_app(app)
    login_manager_manutencao.login_view = "login"
    login_manager_manutencao.login_message = "Faça login de administrador para continuar."
    login_manager_manutencao.login_message_category = "erro"

    @login_manager_manutencao.user_loader
    def carregar_usuario(user_id):
        return Usuario.query.get(int(user_id))

    @app.before_request
    def _exigir_admin():
        if request.endpoint in ("login", "login_salvar", "static"):
            return None
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        if not current_user.is_admin:
            logout_user()
            flash("Só administradores acessam esta porta.", "erro")
            return redirect(url_for("login"))
        return None

    @app.get("/login")
    def login():
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for("painel"))
        return render_template("manutencao_login.html")

    @app.post("/login")
    def login_salvar():
        login_informado = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(login=login_informado).first()

        if not usuario or not usuario.ativo or not usuario.is_admin or not usuario.checar_senha(senha):
            flash("Login ou senha inválidos, ou usuário não é administrador.", "erro")
            return render_template("manutencao_login.html", login=login_informado), 401

        login_user(usuario)
        return redirect(url_for("painel"))

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.get("/")
    def painel():
        config = ConfiguracaoManutencao.obter()
        return render_template("manutencao_painel.html", config=config)

    @app.post("/")
    def salvar():
        config = ConfiguracaoManutencao.obter()
        config.ativo = request.form.get("ativo") == "on"
        config.titulo = request.form.get("titulo", "").strip() or "Sistema em manutenção"
        config.mensagem = request.form.get("mensagem", "").strip()

        previsao = request.form.get("previsao_retorno", "").strip()
        config.previsao_retorno = datetime.fromisoformat(previsao) if previsao else None

        config.atualizado_por_id = current_user.id
        config.atualizado_em = datetime.utcnow()
        db.session.commit()

        flash("Configuração de manutenção atualizada.", "ok")
        return redirect(url_for("painel"))

    with app.app_context():
        from app import models  # noqa: F401 — garante que os modelos sejam registrados
        db.create_all()

    return app


def main():
    app = create_manutencao_app()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
