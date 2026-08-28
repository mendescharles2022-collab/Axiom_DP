import os

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from app.extensions import db
from app.models.empresa import Empresa
from app.models.empregado import Empregado
from app.models.frase_quitacao import FraseQuitacao
from app.models.recibo_avulso import ReciboAvulso, ReciboAvulsoItem
from app.models.rubrica import Rubrica
from app.models.template_recibo import TemplateRecibo
from app.services.calculo_folha import CalculoFolhaError, montar_calculo_recibo
from app.services.recibo_engine import GeracaoReciboError, gerar_recibo_docx

recibos_bp = Blueprint("recibos", __name__)


@recibos_bp.before_request
@login_required
def _exigir_login():
    return None


LINHAS_ITEM_PADRAO = 8


@recibos_bp.get("/empresas/<int:empresa_id>/recibos")
def listar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    recibos = (
        ReciboAvulso.query.filter_by(empresa_id=empresa_id)
        .order_by(ReciboAvulso.competencia.desc(), ReciboAvulso.id.desc())
        .all()
    )
    return render_template("recibos_lista.html", empresa=empresa, recibos=recibos)


@recibos_bp.get("/empresas/<int:empresa_id>/recibos/novo")
def novo_form(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    empregados = Empregado.query.filter_by(empresa_id=empresa_id).order_by(Empregado.nome_completo).all()
    rubricas = Rubrica.query.order_by(Rubrica.codigo).all()
    frases = FraseQuitacao.query.order_by(FraseQuitacao.nome).all()
    templates_recibo = TemplateRecibo.query.filter_by(ativo=True).order_by(TemplateRecibo.tipo, TemplateRecibo.nome).all()
    return render_template(
        "recibo_form.html",
        empresa=empresa, empregados=empregados, rubricas=rubricas, frases=frases,
        templates_recibo=templates_recibo, linhas=range(LINHAS_ITEM_PADRAO),
    )


@recibos_bp.post("/empresas/<int:empresa_id>/recibos/novo")
def novo_salvar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)

    tipo = request.form.get("tipo", "contracheque")
    competencia = request.form.get("competencia", "").strip()
    empregado_id = request.form.get("empregado_id", type=int)
    nome_pro_labore = request.form.get("nome_pro_labore", "").strip() or None
    frase_quitacao_id = request.form.get("frase_quitacao_id", type=int) or empresa.frase_quitacao_padrao_id
    template_recibo_id = request.form.get("template_recibo_id", type=int)

    erro = None
    if not competencia:
        erro = "Informe a competência (mês/ano)."
    elif tipo == "contracheque" and not empregado_id:
        erro = "Selecione o empregado."
    elif tipo == "pro_labore" and not empregado_id and not nome_pro_labore:
        erro = "Informe o nome do sócio para o pró-labore (ou selecione um empregado, se ele também tiver registro)."

    if empregado_id:
        empregado = Empregado.query.get(empregado_id)
        if not empregado or empregado.empresa_id != empresa_id:
            erro = "Empregado não pertence a esta empresa."

    if erro:
        flash(erro, "erro")
        return redirect(url_for("recibos.novo_form", empresa_id=empresa_id))

    recibo = ReciboAvulso(
        empresa_id=empresa_id,
        empregado_id=empregado_id or None,
        nome_pro_labore=nome_pro_labore if not empregado_id else None,
        competencia=competencia,
        tipo=tipo,
        frase_quitacao_id=frase_quitacao_id,
        template_recibo_id=template_recibo_id,
    )
    db.session.add(recibo)
    db.session.flush()

    total_itens = 0
    rubricas_nao_encontradas = []
    for i in range(LINHAS_ITEM_PADRAO):
        texto_rubrica = request.form.get(f"rubrica_texto_{i}", "").strip()
        if not texto_rubrica:
            continue
        provento = request.form.get(f"valor_provento_{i}", "").strip()
        desconto = request.form.get(f"valor_desconto_{i}", "").strip()
        if not provento and not desconto:
            continue

        rubrica = _resolver_rubrica(texto_rubrica)
        if not rubrica:
            rubricas_nao_encontradas.append(texto_rubrica)
            continue

        db.session.add(ReciboAvulsoItem(
            recibo_id=recibo.id,
            rubrica_id=rubrica.id,
            referencia=request.form.get(f"referencia_{i}", "").strip() or None,
            valor_provento=_parse_valor(provento),
            valor_desconto=_parse_valor(desconto),
        ))
        total_itens += 1

    if rubricas_nao_encontradas:
        db.session.rollback()
        flash(
            "Rubrica não encontrada (escolha uma opção da lista sugerida): "
            + ", ".join(rubricas_nao_encontradas),
            "erro",
        )
        return redirect(url_for("recibos.novo_form", empresa_id=empresa_id))

    if total_itens == 0:
        db.session.rollback()
        flash("Adicione pelo menos um item (rubrica) ao recibo.", "erro")
        return redirect(url_for("recibos.novo_form", empresa_id=empresa_id))

    db.session.commit()
    return redirect(url_for("recibos.detalhe", recibo_id=recibo.id))


def _resolver_rubrica(texto_digitado: str):
    """
    O campo de rubrica é um texto livre com sugestão via <datalist> (ao
    invés de um <select> com as 1.798 rubricas repetido em cada linha,
    que deixava a página lenta para renderizar). Aceita "codigo — nome"
    (como sugerido no datalist) ou só o código.
    """
    codigo_texto = texto_digitado.split("—")[0].strip()
    if not codigo_texto.isdigit():
        return None
    return Rubrica.query.filter_by(codigo=int(codigo_texto)).first()


def _parse_valor(texto):
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


@recibos_bp.get("/recibos/<int:recibo_id>")
def detalhe(recibo_id):
    recibo = ReciboAvulso.query.get_or_404(recibo_id)
    try:
        resultado = montar_calculo_recibo(recibo)
        erro_calculo = None
    except CalculoFolhaError as exc:
        resultado = None
        erro_calculo = str(exc)
    return render_template("recibo_detalhe.html", recibo=recibo, resultado=resultado, erro_calculo=erro_calculo)


@recibos_bp.post("/recibos/<int:recibo_id>/gerar")
def gerar(recibo_id):
    recibo = ReciboAvulso.query.get_or_404(recibo_id)
    try:
        resultado = montar_calculo_recibo(recibo)
        caminho = gerar_recibo_docx(recibo, resultado)
    except (CalculoFolhaError, GeracaoReciboError) as exc:
        flash(f"Erro ao gerar o recibo: {exc}", "erro")
        return redirect(url_for("recibos.detalhe", recibo_id=recibo_id))

    recibo.caminho_arquivo_gerado = caminho
    db.session.commit()
    flash("Recibo gerado com sucesso.", "ok")
    return redirect(url_for("recibos.detalhe", recibo_id=recibo_id))


@recibos_bp.get("/recibos/<int:recibo_id>/baixar")
def baixar(recibo_id):
    recibo = ReciboAvulso.query.get_or_404(recibo_id)
    if not recibo.caminho_arquivo_gerado:
        flash("Este recibo ainda não foi gerado.", "erro")
        return redirect(url_for("recibos.detalhe", recibo_id=recibo_id))
    nome_arquivo = os.path.basename(recibo.caminho_arquivo_gerado)
    return send_file(recibo.caminho_arquivo_gerado, as_attachment=True, download_name=nome_arquivo)


@recibos_bp.post("/recibos/<int:recibo_id>/excluir")
def excluir(recibo_id):
    recibo = ReciboAvulso.query.get_or_404(recibo_id)
    empresa_id = recibo.empresa_id
    db.session.delete(recibo)
    db.session.commit()
    flash("Recibo excluído.", "ok")
    return redirect(url_for("recibos.listar", empresa_id=empresa_id))
