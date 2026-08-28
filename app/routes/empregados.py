from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.extensions import db
from app.models.empregado import Empregado
from app.models.empresa import Empresa

empregados_bp = Blueprint("empregados", __name__)


@empregados_bp.before_request
def _exigir_login_api():
    if not current_user.is_authenticated:
        return jsonify({"erro": "Autenticação necessária."}), 401


@empregados_bp.get("/")
def listar_empregados():
    empresa_id = request.args.get("empresa_id", type=int)
    query = Empregado.query
    if empresa_id:
        query = query.filter_by(empresa_id=empresa_id)
    empregados = query.order_by(Empregado.nome_completo).all()
    return jsonify([e.to_dict() for e in empregados])


@empregados_bp.get("/<int:empregado_id>")
def obter_empregado(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    return jsonify(empregado.to_dict())


@empregados_bp.post("/")
def criar_empregado():
    dados = request.get_json(force=True)
    if not dados.get("nome_completo") or not dados.get("cpf") or not dados.get("empresa_id"):
        return jsonify({"erro": "nome_completo, cpf e empresa_id são obrigatórios."}), 400

    if not Empresa.query.get(dados["empresa_id"]):
        return jsonify({"erro": "Empresa informada não existe."}), 404

    empregado = Empregado(
        empresa_id=dados["empresa_id"],
        nome_completo=dados.get("nome_completo"),
        cpf=dados.get("cpf"),
        rg=dados.get("rg"),
        data_nascimento=dados.get("data_nascimento"),
        nacionalidade=dados.get("nacionalidade", "brasileira"),
        estado_civil=dados.get("estado_civil"),
        ctps_numero=dados.get("ctps_numero"),
        ctps_serie=dados.get("ctps_serie"),
        pis_pasep=dados.get("pis_pasep"),
        endereco=dados.get("endereco"),
        telefone=dados.get("telefone"),
        email=dados.get("email"),
        cargo=dados.get("cargo"),
        setor=dados.get("setor"),
        tipo_contrato=dados.get("tipo_contrato", "indeterminado"),
        data_admissao=dados.get("data_admissao"),
        jornada_semanal_horas=dados.get("jornada_semanal_horas"),
        salario_base=dados.get("salario_base"),
        numero_dependentes_irrf=dados.get("numero_dependentes_irrf", 0),
        numero_dependentes_salario_familia=dados.get("numero_dependentes_salario_familia", 0),
        banco=dados.get("banco"),
        agencia=dados.get("agencia"),
        conta=dados.get("conta"),
        chave_pix=dados.get("chave_pix"),
    )
    db.session.add(empregado)
    db.session.commit()
    return jsonify(empregado.to_dict()), 201


@empregados_bp.put("/<int:empregado_id>")
def atualizar_empregado(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    dados = request.get_json(force=True)
    for campo in [
        "nome_completo", "cpf", "rg", "data_nascimento", "nacionalidade", "estado_civil",
        "ctps_numero", "ctps_serie", "pis_pasep", "endereco", "telefone", "email",
        "cargo", "setor", "tipo_contrato", "data_admissao", "data_desligamento",
        "jornada_semanal_horas", "salario_base", "numero_dependentes_irrf",
        "numero_dependentes_salario_familia", "banco", "agencia", "conta",
        "chave_pix", "ativo", "observacoes",
    ]:
        if campo in dados:
            setattr(empregado, campo, dados[campo])
    db.session.commit()
    return jsonify(empregado.to_dict())


@empregados_bp.delete("/<int:empregado_id>")
def excluir_empregado(empregado_id):
    empregado = Empregado.query.get_or_404(empregado_id)
    db.session.delete(empregado)
    db.session.commit()
    return jsonify({"ok": True})
