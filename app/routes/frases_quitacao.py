from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth_decorators import admin_required
from app.extensions import db
from app.models.frase_quitacao import FraseQuitacao

frases_quitacao_bp = Blueprint("frases_quitacao", __name__)


@frases_quitacao_bp.get("/")
@admin_required
def listar():
    frases = FraseQuitacao.query.order_by(FraseQuitacao.nome).all()
    return render_template("frases_quitacao_lista.html", frases=frases)


@frases_quitacao_bp.get("/nova")
@admin_required
def nova_form():
    return render_template("frase_quitacao_form.html", frase=None)


@frases_quitacao_bp.post("/nova")
@admin_required
def nova_salvar():
    nome = request.form.get("nome", "").strip()
    texto = request.form.get("texto", "").strip()
    if not nome or not texto:
        flash("Nome e texto são obrigatórios.", "erro")
        return render_template("frase_quitacao_form.html", frase={"nome": nome, "texto": texto})

    frase = FraseQuitacao(nome=nome, texto=texto)
    db.session.add(frase)
    db.session.commit()
    flash(f'Frase "{frase.nome}" cadastrada.', "ok")
    return redirect(url_for("frases_quitacao.listar"))


@frases_quitacao_bp.get("/<int:frase_id>/editar")
@admin_required
def editar_form(frase_id):
    frase = FraseQuitacao.query.get_or_404(frase_id)
    return render_template("frase_quitacao_form.html", frase=frase)


@frases_quitacao_bp.post("/<int:frase_id>/editar")
@admin_required
def editar_salvar(frase_id):
    frase = FraseQuitacao.query.get_or_404(frase_id)
    nome = request.form.get("nome", "").strip()
    texto = request.form.get("texto", "").strip()
    if not nome or not texto:
        flash("Nome e texto são obrigatórios.", "erro")
        return render_template("frase_quitacao_form.html", frase=frase)

    frase.nome = nome
    frase.texto = texto
    db.session.commit()
    flash("Frase atualizada.", "ok")
    return redirect(url_for("frases_quitacao.listar"))


@frases_quitacao_bp.post("/<int:frase_id>/excluir")
@admin_required
def excluir(frase_id):
    frase = FraseQuitacao.query.get_or_404(frase_id)
    db.session.delete(frase)
    db.session.commit()
    flash("Frase excluída.", "ok")
    return redirect(url_for("frases_quitacao.listar"))
