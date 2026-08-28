from datetime import datetime
from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.empresa import Empresa
from app.services.cnpj_service import consultar_cnpj, CnpjConsultaError

empresas_bp = Blueprint("empresas", __name__)


@empresas_bp.get("/")
def listar_empresas():
    empresas = Empresa.query.order_by(Empresa.razao_social).all()
    return jsonify([e.to_dict() for e in empresas])


@empresas_bp.get("/<int:empresa_id>")
def obter_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    return jsonify(empresa.to_dict())


@empresas_bp.post("/")
def criar_empresa():
    dados = request.get_json(force=True)
    if not dados.get("razao_social") or not dados.get("cnpj"):
        return jsonify({"erro": "razao_social e cnpj são obrigatórios."}), 400

    if Empresa.query.filter_by(cnpj=dados["cnpj"]).first():
        return jsonify({"erro": "Já existe uma empresa cadastrada com este CNPJ."}), 409

    empresa = Empresa(
        razao_social=dados.get("razao_social"),
        nome_fantasia=dados.get("nome_fantasia"),
        cnpj=dados.get("cnpj"),
        inscricao_estadual=dados.get("inscricao_estadual"),
        logradouro=dados.get("logradouro"),
        numero=dados.get("numero"),
        complemento=dados.get("complemento"),
        bairro=dados.get("bairro"),
        municipio=dados.get("municipio"),
        uf=dados.get("uf"),
        cep=dados.get("cep"),
        cnae_principal=dados.get("cnae_principal"),
        situacao_cadastral=dados.get("situacao_cadastral"),
        data_abertura=dados.get("data_abertura"),
        natureza_juridica=dados.get("natureza_juridica"),
    )
    db.session.add(empresa)
    db.session.commit()
    return jsonify(empresa.to_dict()), 201


@empresas_bp.put("/<int:empresa_id>")
def atualizar_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    dados = request.get_json(force=True)
    for campo in [
        "razao_social", "nome_fantasia", "cnpj", "inscricao_estadual",
        "logradouro", "numero", "complemento", "bairro", "municipio", "uf", "cep",
        "cnae_principal", "situacao_cadastral", "data_abertura", "natureza_juridica",
        "ativo", "observacoes",
    ]:
        if campo in dados:
            setattr(empresa, campo, dados[campo])
    db.session.commit()
    return jsonify(empresa.to_dict())


@empresas_bp.delete("/<int:empresa_id>")
def excluir_empresa(empresa_id):
    empresa = Empresa.query.get_or_404(empresa_id)
    db.session.delete(empresa)
    db.session.commit()
    return jsonify({"ok": True})


@empresas_bp.get("/consultar-cnpj/<cnpj>")
def consultar_cnpj_route(cnpj):
    """Consulta a BrasilAPI e devolve os dados prontos para pré-preencher o formulário."""
    try:
        dados = consultar_cnpj(cnpj)
    except CnpjConsultaError as exc:
        return jsonify({"erro": str(exc)}), 400
    dados["ultima_consulta_api"] = datetime.utcnow().isoformat()
    return jsonify(dados)
