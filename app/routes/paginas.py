import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from app.extensions import db
from app.models.empresa import Empresa
from app.models.empregado import Empregado
from app.models.documento import TemplateDocumento
from app.models.emissao import DocumentoEmitido
from app.services.cnpj_service import consultar_cnpj, CnpjConsultaError
from app.services.document_engine import gerar_documento, GeracaoDocumentoError

paginas_bp = Blueprint("paginas", __name__)


@paginas_bp.before_request
@login_required
def _exigir_login():
    return None

TIPOS_CONTRATO = [
    ("indeterminado", "Prazo indeterminado"),
    ("experiencia", "Experiência"),
    ("tempo_parcial", "Tempo parcial"),
    ("temporario", "Temporário (Lei 6.019/74)"),
    ("obra_certa", "Obra certa"),
    ("safra", "Safra rural"),
    ("intermitente", "Intermitente"),
    ("aprendiz", "Aprendizagem"),
    ("estagio", "Estágio"),
]


def _campos_empresa_do_form(form):
    return dict(
        razao_social=form.get("razao_social", "").strip(),
        nome_fantasia=form.get("nome_fantasia", "").strip() or None,
        cnpj=form.get("cnpj", "").strip(),
        inscricao_estadual=form.get("inscricao_estadual", "").strip() or None,
        logradouro=form.get("logradouro", "").strip() or None,
        numero=form.get("numero", "").strip() or None,
        complemento=form.get("complemento", "").strip() or None,
        bairro=form.get("bairro", "").strip() or None,
        municipio=form.get("municipio", "").strip() or None,
        uf=(form.get("uf", "").strip() or None),
        cep=form.get("cep", "").strip() or None,
        cnae_principal=form.get("cnae_principal", "").strip() or None,
        situacao_cadastral=form.get("situacao_cadastral", "").strip() or None,
        data_abertura=form.get("data_abertura", "").strip() or None,
        natureza_juridica=form.get("natureza_juridica", "").strip() or None,
        observacoes=form.get("observacoes", "").strip() or None,
    )


def _campos_empregado_do_form(form):
    salario = form.get("salario_base", "").strip().replace(",", ".")
    jornada = form.get("jornada_semanal_horas", "").strip().replace(",", ".")
    return dict(
        nome_completo=form.get("nome_completo", "").strip(),
        cpf=form.get("cpf", "").strip(),
        rg=form.get("rg", "").strip() or None,
        data_nascimento=form.get("data_nascimento", "").strip() or None,
        nacionalidade=form.get("nacionalidade", "brasileira").strip() or "brasileira",
        estado_civil=form.get("estado_civil", "").strip() or None,
        ctps_numero=form.get("ctps_numero", "").strip() or None,
        ctps_serie=form.get("ctps_serie", "").strip() or None,
        pis_pasep=form.get("pis_pasep", "").strip() or None,
        endereco=form.get("endereco", "").strip() or None,
        telefone=form.get("telefone", "").strip() or None,
        email=form.get("email", "").strip() or None,
        cargo=form.get("cargo", "").strip() or None,
        setor=form.get("setor", "").strip() or None,
        tipo_contrato=form.get("tipo_contrato", "indeterminado"),
        data_admissao=form.get("data_admissao", "").strip() or None,
        data_desligamento=form.get("data_desligamento", "").strip() or None,
        jornada_semanal_horas=float(jornada) if jornada else None,
        salario_base=float(salario) if salario else None,
        banco=form.get("banco", "").strip() or None,
        agencia=form.get("agencia", "").strip() or None,
        conta=form.get("conta", "").strip() or None,
        chave_pix=form.get("chave_pix", "").strip() or None,
        observacoes=form.get("observacoes", "").strip() or None,
    )


# ---------------------------------------------------------------- Dashboard
@paginas_bp.get("/")
def index():
    busca = request.args.get("q", "").strip()
    query = Empresa.query
    if busca:
        like = f"%{busca}%"
        query = query.filter(
            db.or_(Empresa.razao_social.ilike(like), Empresa.cnpj.ilike(like))
        )
    empresas = query.order_by(Empresa.razao_social).all()
    return render_template("empresas_lista.html", empresas=empresas, busca=busca)


# ---------------------------------------------------------------- Empresas
@paginas_bp.get("/empresas/nova")
def empresa_nova_form():
    return render_template("empresa_form.html", empresa=None)


@paginas_bp.post("/empresas/nova")
def empresa_nova_salvar():
    dados = _campos_empresa_do_form(request.form)
    if not dados["razao_social"] or not dados["cnpj"]:
        flash("Razão social e CNPJ são obrigatórios.", "erro")
        return render_template("empresa_form.html", empresa=dados)

    if Empresa.query.filter_by(cnpj=dados["cnpj"]).first():
        flash("Já existe uma empresa cadastrada com este CNPJ.", "erro")
        return render_template("empresa_form.html", empresa=dados)

    empresa = Empresa(**dados)
    db.session.add(empresa)
    db.session.commit()
    flash(f"Empresa \"{empresa.razao_social}\" cadastrada com sucesso.", "ok")
    return redirect(url_for("paginas.empresa_detalhe", empresa_id=empresa.id))


@paginas_bp.get("/empresas/<int:empresa_id>")
def empresa_detalhe(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    empregados = (
        Empregado.query.filter_by(empresa_id=empresa_id)
        .order_by(Empregado.nome_completo)
        .all()
    )
    return render_template("empresa_detalhe.html", empresa=empresa, empregados=empregados)


@paginas_bp.get("/empresas/<int:empresa_id>/editar")
def empresa_editar_form(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    return render_template("empresa_form.html", empresa=empresa)


@paginas_bp.post("/empresas/<int:empresa_id>/editar")
def empresa_editar_salvar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    dados = _campos_empresa_do_form(request.form)
    if not dados["razao_social"] or not dados["cnpj"]:
        flash("Razão social e CNPJ são obrigatórios.", "erro")
        dados["id"] = empresa_id
        return render_template("empresa_form.html", empresa=dados)

    duplicada = Empresa.query.filter(
        Empresa.cnpj == dados["cnpj"], Empresa.id != empresa_id
    ).first()
    if duplicada:
        flash("Já existe outra empresa cadastrada com este CNPJ.", "erro")
        dados["id"] = empresa_id
        return render_template("empresa_form.html", empresa=dados)

    for campo, valor in dados.items():
        setattr(empresa, campo, valor)
    db.session.commit()
    flash("Dados da empresa atualizados.", "ok")
    return redirect(url_for("paginas.empresa_detalhe", empresa_id=empresa.id))


@paginas_bp.post("/empresas/<int:empresa_id>/excluir")
def empresa_excluir(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    nome = empresa.razao_social
    db.session.delete(empresa)
    db.session.commit()
    flash(f"Empresa \"{nome}\" e seus empregados foram excluídos.", "ok")
    return redirect(url_for("paginas.index"))


@paginas_bp.get("/empresas/buscar-cnpj")
def empresa_buscar_cnpj_form():
    """Usado pelo botão de busca dentro do próprio formulário (via fetch)."""
    cnpj = request.args.get("cnpj", "")
    try:
        dados = consultar_cnpj(cnpj)
        return dados
    except CnpjConsultaError as exc:
        return {"erro": str(exc)}, 400


# ---------------------------------------------------------------- Empregados
@paginas_bp.get("/empresas/<int:empresa_id>/empregados/novo")
def empregado_novo_form(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    return render_template(
        "empregado_form.html", empresa=empresa, empregado=None, tipos_contrato=TIPOS_CONTRATO
    )


@paginas_bp.post("/empresas/<int:empresa_id>/empregados/novo")
def empregado_novo_salvar(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    dados = _campos_empregado_do_form(request.form)
    if not dados["nome_completo"] or not dados["cpf"]:
        flash("Nome completo e CPF são obrigatórios.", "erro")
        return render_template(
            "empregado_form.html", empresa=empresa, empregado=dados, tipos_contrato=TIPOS_CONTRATO
        )

    empregado = Empregado(empresa_id=empresa_id, **dados)
    db.session.add(empregado)
    db.session.commit()
    flash(f"Empregado \"{empregado.nome_completo}\" cadastrado com sucesso.", "ok")
    return redirect(url_for("paginas.empresa_detalhe", empresa_id=empresa_id))


@paginas_bp.get("/empregados/<int:empregado_id>/editar")
def empregado_editar_form(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    return render_template(
        "empregado_form.html",
        empresa=empregado.empresa,
        empregado=empregado,
        tipos_contrato=TIPOS_CONTRATO,
    )


@paginas_bp.post("/empregados/<int:empregado_id>/editar")
def empregado_editar_salvar(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    dados = _campos_empregado_do_form(request.form)
    if not dados["nome_completo"] or not dados["cpf"]:
        flash("Nome completo e CPF são obrigatórios.", "erro")
        dados["id"] = empregado_id
        return render_template(
            "empregado_form.html",
            empresa=empregado.empresa,
            empregado=dados,
            tipos_contrato=TIPOS_CONTRATO,
        )

    for campo, valor in dados.items():
        setattr(empregado, campo, valor)
    db.session.commit()
    flash("Dados do empregado atualizados.", "ok")
    return redirect(url_for("paginas.empresa_detalhe", empresa_id=empregado.empresa_id))


@paginas_bp.post("/empregados/<int:empregado_id>/excluir")
def empregado_excluir(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    empresa_id = empregado.empresa_id
    nome = empregado.nome_completo
    db.session.delete(empregado)
    db.session.commit()
    flash(f"Empregado \"{nome}\" excluído.", "ok")
    return redirect(url_for("paginas.empresa_detalhe", empresa_id=empresa_id))


# ---------------------------------------------------------------- Emissão de documentos
@paginas_bp.get("/empresas/<int:empresa_id>/emitir")
def emitir_catalogo(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    empregados = Empregado.query.filter_by(empresa_id=empresa_id).order_by(Empregado.nome_completo).all()

    templates = TemplateDocumento.query.filter_by(ativo=True).order_by(
        TemplateDocumento.categoria, TemplateDocumento.nome
    ).all()
    categorias = {}
    for t in templates:
        categorias.setdefault(t.categoria, []).append(t)

    return render_template(
        "emitir_catalogo.html", empresa=empresa, empregados=empregados, categorias=categorias
    )


@paginas_bp.get("/empresas/<int:empresa_id>/emitir/<int:template_id>")
def emitir_form(empresa_id, template_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    template = TemplateDocumento.query.get_or_404(template_id)
    empregados = Empregado.query.filter_by(empresa_id=empresa_id).order_by(Empregado.nome_completo).all()

    if not empregados:
        flash("Cadastre pelo menos um empregado nesta empresa antes de emitir um documento.", "erro")
        return redirect(url_for("paginas.empresa_detalhe", empresa_id=empresa_id))

    return render_template(
        "emitir_form.html", empresa=empresa, template=template, empregados=empregados
    )


@paginas_bp.post("/empresas/<int:empresa_id>/emitir/<int:template_id>")
def emitir_gerar(empresa_id, template_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    template = TemplateDocumento.query.get_or_404(template_id)

    empregado_id = request.form.get("empregado_id", type=int)
    empregado = Empregado.query.get_or_404(empregado_id) if empregado_id else None
    if empregado and empregado.empresa_id != empresa_id:
        flash("Empregado não pertence a esta empresa.", "erro")
        return redirect(url_for("paginas.emitir_form", empresa_id=empresa_id, template_id=template_id))

    data_emissao = request.form.get("data_emissao") or None
    extra = {
        campo["nome"]: request.form.get(f"extra_{campo['nome']}", "").strip()
        for campo in template.campos_extra()
    }

    try:
        caminho, registro = gerar_documento(template, empresa, empregado, extra, data_emissao=data_emissao)
    except GeracaoDocumentoError as exc:
        flash(f"Erro ao gerar o documento: {exc}", "erro")
        return redirect(url_for("paginas.emitir_form", empresa_id=empresa_id, template_id=template_id))

    flash(f"Documento \"{template.nome}\" gerado com sucesso.", "ok")
    return redirect(url_for("paginas.emitir_pronto", documento_id=registro.id))


@paginas_bp.get("/documentos/<int:documento_id>/pronto")
def emitir_pronto(documento_id):
    documento = DocumentoEmitido.query.get_or_404(documento_id)
    return render_template("emitir_pronto.html", documento=documento)


@paginas_bp.get("/documentos/<int:documento_id>/baixar")
def documento_baixar(documento_id):
    documento = DocumentoEmitido.query.get_or_404(documento_id)
    nome_arquivo = os.path.basename(documento.caminho_arquivo_gerado)
    return send_file(documento.caminho_arquivo_gerado, as_attachment=True, download_name=nome_arquivo)


@paginas_bp.get("/empresas/<int:empresa_id>/historico")
def historico_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    documentos = (
        DocumentoEmitido.query.filter_by(empresa_id=empresa_id)
        .order_by(DocumentoEmitido.emitido_em.desc())
        .all()
    )
    return render_template("historico.html", empresa=empresa, documentos=documentos)
