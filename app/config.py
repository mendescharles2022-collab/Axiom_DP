import os
import sys


def _secret_key() -> str:
    """
    Chave de assinatura de sessão. Definir AXIOM_DP_SECRET_KEY é o
    recomendado em produção; sem ela, gera uma chave aleatória na primeira
    execução e a mantém em um arquivo dentro de DATA_DIR (fora do controle
    de versão), para que as sessões sobrevivam a reinícios do servidor sem
    depender de uma chave fixa no código-fonte.
    """
    env = os.environ.get("AXIOM_DP_SECRET_KEY")
    if env:
        return env

    caminho = os.path.join(DATA_DIR, "secret_key")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            chave = f.read().strip()
        if chave:
            return chave

    chave = os.urandom(32).hex()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(chave)
    return chave


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
DOCS_TEMPLATES_RECIBO_DIR = os.path.join(BASE_DIR, "app", "docs_templates_recibo")
OUTPUT_DIR = os.path.join(DATA_DIR, "documentos_gerados")


class Config:
    SECRET_KEY = _secret_key()
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 15},
    }

    @staticmethod
    def ensure_dirs():
        os.makedirs(DATABASE_DIR, exist_ok=True)
        os.makedirs(DOCS_TEMPLATES_DIR, exist_ok=True)
        os.makedirs(DOCS_TEMPLATES_RECIBO_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
