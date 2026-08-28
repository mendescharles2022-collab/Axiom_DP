import os
import sys


def _data_dir_padrao() -> str:
    """
    Pasta padrão para dados persistentes (banco, documentos gerados) quando
    AXIOM_DP_DATA_DIR não é definida. Fica FORA da pasta de instalação do
    programa para que atualizações não arrisquem o banco de dados.
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Axiom_DP")
    return os.path.join(os.path.expanduser("~"), ".axiom_dp")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("AXIOM_DP_DATA_DIR") or _data_dir_padrao()
DATABASE_DIR = os.path.join(DATA_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "axiom_dp.sqlite3")
DOCS_TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "docs_templates")
OUTPUT_DIR = os.path.join(DATA_DIR, "documentos_gerados")


class Config:
    SECRET_KEY = "axiom-dp-local-secret"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 15},
    }

    @staticmethod
    def ensure_dirs():
        os.makedirs(DATABASE_DIR, exist_ok=True)
        os.makedirs(DOCS_TEMPLATES_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
