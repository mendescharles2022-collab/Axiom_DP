from flask import Flask, render_template, request
from flask_login import current_user

from app.config import Config
from app.extensions import db, login_manager
from app.utils.texto import titulo_pt

# Endpoints que continuam acessíveis mesmo com o modo manutenção ligado —
# precisam funcionar para um admin conseguir logar e para os arquivos
# estáticos da própria página de aviso carregarem.
_ENDPOINTS_LIVRES_DE_MANUTENCAO = {"static", "auth.login", "auth.login_salvar", "auth.logout"}


def create_app(config_overrides: dict | None = None):
    Config.ensure_dirs()

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    app.jinja_env.filters["titulo_pt"] = titulo_pt

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "erro"

    @login_manager.user_loader
    def carregar_usuario(user_id):
        from app.models.usuario import Usuario
        return Usuario.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.empresas import empresas_bp
    from app.routes.empregados import empregados_bp
    from app.routes.paginas import paginas_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.recibos import recibos_bp
    from app.routes.frases_quitacao import frases_quitacao_bp
    from app.routes.relatorios import relatorios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(paginas_bp)
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(recibos_bp)
    app.register_blueprint(frases_quitacao_bp, url_prefix="/frases-quitacao")
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(empresas_bp, url_prefix="/api/empresas")
    app.register_blueprint(empregados_bp, url_prefix="/api/empregados")

    @app.before_request
    def _checar_modo_manutencao():
        if request.endpoint in _ENDPOINTS_LIVRES_DE_MANUTENCAO:
            return None
        if current_user.is_authenticated and current_user.is_admin:
            return None

        from app.models.configuracao_manutencao import ConfiguracaoManutencao

        config = ConfiguracaoManutencao.query.get(1)
        if config and config.ativo:
            return render_template("manutencao.html", config=config), 503
        return None

    with app.app_context():
        from app import models  # noqa: F401 — garante que os modelos sejam registrados
        db.create_all()

    return app
