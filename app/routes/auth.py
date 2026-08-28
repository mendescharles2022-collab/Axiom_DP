from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login():
    if Usuario.query.count() == 0:
        return redirect(url_for("auth.primeiro_acesso"))
    if current_user.is_authenticated:
        return redirect(url_for("paginas.index"))
    return render_template("login.html")


@auth_bp.post("/login")
def login_salvar():
    if Usuario.query.count() == 0:
        return redirect(url_for("auth.primeiro_acesso"))

    login_informado = request.form.get("login", "").strip()
    senha = request.form.get("senha", "")
    usuario = Usuario.query.filter_by(login=login_informado).first()

    if not usuario or not usuario.ativo or not usuario.checar_senha(senha):
        flash("Login ou senha inválidos.", "erro")
        return render_template("login.html", login=login_informado), 401

    usuario.ultimo_acesso = datetime.utcnow()
    db.session.commit()
    login_user(usuario)
    return redirect(url_for("paginas.index"))


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "ok")
    return redirect(url_for("auth.login"))


@auth_bp.get("/primeiro-acesso")
def primeiro_acesso():
    if Usuario.query.count() > 0:
        return redirect(url_for("auth.login"))
    return render_template("primeiro_acesso.html")


@auth_bp.post("/primeiro-acesso")
def primeiro_acesso_salvar():
    if Usuario.query.count() > 0:
        return redirect(url_for("auth.login"))

    nome = request.form.get("nome", "").strip()
    login_informado = request.form.get("login", "").strip()
    senha = request.form.get("senha", "")
    confirmar_senha = request.form.get("confirmar_senha", "")

    erro = None
    if not nome or not login_informado or not senha:
        erro = "Preencha todos os campos."
    elif len(senha) < 8:
        erro = "A senha deve ter pelo menos 8 caracteres."
    elif senha != confirmar_senha:
        erro = "As senhas não conferem."

    if erro:
        flash(erro, "erro")
        return render_template("primeiro_acesso.html", nome=nome, login=login_informado)

    usuario = Usuario(nome=nome, login=login_informado, perfil="admin", ativo=True)
    usuario.set_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    flash("Administrador criado com sucesso. Faça login para continuar.", "ok")
    return redirect(url_for("auth.login"))
