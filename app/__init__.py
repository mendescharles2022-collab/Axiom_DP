from flask import Flask
from app.config import Config
from app.extensions import db, login_manager
from app.utils.texto import titulo_pt


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

    app.register_blueprint(auth_bp)
    app.register_blueprint(paginas_bp)
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(recibos_bp)
    app.register_blueprint(frases_quitacao_bp, url_prefix="/frases-quitacao")
    app.register_blueprint(empresas_bp, url_prefix="/api/empresas")
    app.register_blueprint(empregados_bp, url_prefix="/api/empregados")

    with app.app_context():
        from app import models  # noqa: F401 — garante que os modelos sejam registrados
        db.create_all()

    return app
