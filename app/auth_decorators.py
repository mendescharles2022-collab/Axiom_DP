"""
Decorators de permissão usados nas rotas HTML (paginas.py, usuarios.py).
Perfis: "admin" (tudo liberado) e "operador" (uso do dia a dia, sem
gerenciar usuários) — ver HANDOFF_CLAUDE_CODE.md, seção 3.
"""
from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return login_required(wrapper)
