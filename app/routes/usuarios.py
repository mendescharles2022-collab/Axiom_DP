from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.auth_decorators import admin_required
from app.extensions import db
from app.models.usuario import PERFIS_VALIDOS, Usuario

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.get("/")
@admin_required
def listar():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("usuarios_lista.html", usuarios=usuarios)


@usuarios_bp.get("/novo")
@admin_required
def novo_form():
    return render_template("usuario_form.html", usuario=None, perfis=PERFIS_VALIDOS)


@usuarios_bp.post("/novo")
@admin_required
def novo_salvar():
    nome = request.form.get("nome", "").strip()
    login_informado = request.form.get("login", "").strip()
    perfil = request.form.get("perfil", "operador")
    senha = request.form.get("senha", "")

    dados = {"nome": nome, "login": login_informado, "perfil": perfil}

    if not nome or not login_informado or not senha:
        flash("Nome, login e senha são obrigatórios.", "erro")
        return render_template("usuario_form.html", usuario=dados, perfis=PERFIS_VALIDOS)
    if len(senha) < 8:
        flash("A senha deve ter pelo menos 8 caracteres.", "erro")
        return render_template("usuario_form.html", usuario=dados, perfis=PERFIS_VALIDOS)
    if perfil not in PERFIS_VALIDOS:
        flash("Perfil inválido.", "erro")
        return render_template("usuario_form.html", usuario=dados, perfis=PERFIS_VALIDOS)
    if Usuario.query.filter_by(login=login_informado).first():
        flash("Já existe um usuário com este login.", "erro")
        return render_template("usuario_form.html", usuario=dados, perfis=PERFIS_VALIDOS)

    usuario = Usuario(nome=nome, login=login_informado, perfil=perfil, ativo=True)
    usuario.set_senha(senha)
    db.session.add(usuario)
    db.session.commit()
    flash(f'Usuário "{usuario.nome}" cadastrado com sucesso.', "ok")
    return redirect(url_for("usuarios.listar"))


@usuarios_bp.get("/<int:usuario_id>/editar")
@admin_required
def editar_form(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template("usuario_form.html", usuario=usuario, perfis=PERFIS_VALIDOS)


@usuarios_bp.post("/<int:usuario_id>/editar")
@admin_required
def editar_salvar(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    nome = request.form.get("nome", "").strip()
    perfil = request.form.get("perfil", usuario.perfil)
    ativo = request.form.get("ativo") == "on"
    nova_senha = request.form.get("senha", "")

    if not nome:
        flash("Nome é obrigatório.", "erro")
        return render_template("usuario_form.html", usuario=usuario, perfis=PERFIS_VALIDOS)
    if perfil not in PERFIS_VALIDOS:
        flash("Perfil inválido.", "erro")
        return render_template("usuario_form.html", usuario=usuario, perfis=PERFIS_VALIDOS)
    if usuario.id == current_user.id and (perfil != "admin" or not ativo):
        flash("Você não pode remover seu próprio acesso de administrador.", "erro")
        return render_template("usuario_form.html", usuario=usuario, perfis=PERFIS_VALIDOS)
    if nova_senha and len(nova_senha) < 8:
        flash("A nova senha deve ter pelo menos 8 caracteres.", "erro")
        return render_template("usuario_form.html", usuario=usuario, perfis=PERFIS_VALIDOS)

    usuario.nome = nome
    usuario.perfil = perfil
    usuario.ativo = ativo
    if nova_senha:
        usuario.set_senha(nova_senha)

    db.session.commit()
    flash("Dados do usuário atualizados.", "ok")
    return redirect(url_for("usuarios.listar"))
