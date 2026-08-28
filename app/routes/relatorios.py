from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.emissao import DocumentoEmitido
from app.models.empresa import Empresa
from app.models.recibo_avulso import ReciboAvulso

relatorios_bp = Blueprint("relatorios", __name__)


@relatorios_bp.before_request
@login_required
def _exigir_login():
    return None


@relatorios_bp.get("/relatorios")
def historico_geral():
    hoje = datetime.utcnow().date()
    data_inicio = request.args.get("data_inicio") or (hoje - timedelta(days=30)).isoformat()
    data_fim = request.args.get("data_fim") or hoje.isoformat()
    empresa_id = request.args.get("empresa_id", type=int)
    tipo = request.args.get("tipo", "todos")  # todos | documentos | recibos

    inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
    fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)  # inclui o dia inteiro

    documentos = []
    if tipo in ("todos", "documentos"):
        query = DocumentoEmitido.query.filter(
            DocumentoEmitido.emitido_em >= inicio_dt, DocumentoEmitido.emitido_em < fim_dt
        )
        if empresa_id:
            query = query.filter_by(empresa_id=empresa_id)
        documentos = query.order_by(DocumentoEmitido.emitido_em.desc()).all()

    recibos = []
    if tipo in ("todos", "recibos"):
        query = ReciboAvulso.query.filter(
            ReciboAvulso.criado_em >= inicio_dt, ReciboAvulso.criado_em < fim_dt
        )
        if empresa_id:
            query = query.filter_by(empresa_id=empresa_id)
        recibos = query.order_by(ReciboAvulso.criado_em.desc()).all()

    empresas = Empresa.query.order_by(Empresa.razao_social).all()

    return render_template(
        "relatorio.html",
        documentos=documentos, recibos=recibos, empresas=empresas,
        data_inicio=data_inicio, data_fim=data_fim, empresa_id=empresa_id, tipo=tipo,
    )
