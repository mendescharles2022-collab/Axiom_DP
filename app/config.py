import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "axiom_dp.sqlite3")
DOCS_TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "docs_templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "documentos_gerados")


class Config:
    SECRET_KEY = "axiom-dp-local-secret"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def ensure_dirs():
        os.makedirs(DATABASE_DIR, exist_ok=True)
        os.makedirs(DOCS_TEMPLATES_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
