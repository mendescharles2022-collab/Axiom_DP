from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
login_manager = LoginManager()


@event.listens_for(Engine, "connect")
def _ativar_wal_sqlite(dbapi_connection, connection_record):
    """
    Ativa o modo WAL (Write-Ahead Logging) do SQLite em toda conexão nova.
    Permite que várias estações da rede leiam e gravem no banco ao mesmo
    tempo sem travar (ver seção 2 do HANDOFF_CLAUDE_CODE.md).
    """
    if type(dbapi_connection).__module__.split(".")[0] != "sqlite3":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=15000")
    cursor.close()
