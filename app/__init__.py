from flask import Flask
from app.config import Config
from app.extensions import db


def create_app(config_overrides: dict | None = None):
    Config.ensure_dirs()

    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    from app.routes.empresas import empresas_bp
    from app.routes.empregados import empregados_bp
    from app.routes.paginas import paginas_bp

    app.register_blueprint(paginas_bp)
    app.register_blueprint(empresas_bp, url_prefix="/api/empresas")
    app.register_blueprint(empregados_bp, url_prefix="/api/empregados")

    with app.app_context():
        from app import models  # noqa: F401 — garante que os modelos sejam registrados
        db.create_all()

    return app
