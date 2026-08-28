"""
Gera o .docx do recibo avulso (contracheque/pró-labore) a partir do
resultado de app.services.calculo_folha.montar_calculo_recibo(), usando
docxtpl contra o modelo escolhido em app/docs_templates_recibo/ — mesmo
mecanismo dos 48 modelos de DP (app/services/document_engine.py), com um
catálogo de modelos por tipo (TemplateRecibo) em vez de um único layout
fixo (HANDOFF ADENDO seção A).
"""
import os
import re
import unicodedata
from datetime import datetime
from types import SimpleNamespace

from docxtpl import DocxTemplate

from app.config import DOCS_TEMPLATES_RECIBO_DIR, OUTPUT_DIR
from app.models.template_recibo import TemplateRecibo
from app.services.document_engine import MESES_PT, _empresa_contexto, _v
from app.utils.texto import titulo_pt

FRASE_PADRAO = "Declaro que recebi o valor descrito e dou plena quitação do que me é devido até o momento."


class GeracaoReciboError(Exception):
    pass


def _fmt(valor) -> str:
    if valor is None:
        return ""
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _documento_empregador(empresa):
    if empresa.cno:
        return "CNO", empresa.cno
    if empresa.cei:
        return "CEI", empresa.cei
    if empresa.caepf:
        return "CAEPF", empresa.caepf
    return empresa.tipo_inscricao or "CNPJ", empresa.cnpj


def _nome_beneficiario(recibo):
    if recibo.empregado:
        return recibo.empregado.nome_completo
    return recibo.nome_pro_labore or "-"


def _competencia_extenso(competencia: str) -> str:
    ano, mes = competencia.split("-")
    return f"{MESES_PT[int(mes) - 1]}/{ano}"


def _slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto or "recibo"


def escolher_template_padrao(tipo: str):
    return (
        TemplateRecibo.query.filter_by(tipo=tipo, ativo=True)
        .order_by(TemplateRecibo.nome)
        .first()
    )


def _montar_contexto(recibo, resultado):
    empresa_ctx = _empresa_contexto(recibo.empresa)
    doc_rotulo, doc_numero = _documento_empregador(recibo.empresa)
    empresa_ctx.documento_rotulo = doc_rotulo
    empresa_ctx.documento_numero = _v(doc_numero)

    beneficiario_ctx = SimpleNamespace(
        codigo=str(recibo.empregado_id) if recibo.empregado_id else "-",
        nome_completo=_v(titulo_pt(_nome_beneficiario(recibo))),
        cargo=_v(recibo.empregado.cargo) if recibo.empregado and recibo.empregado.cargo else "-",
    )

    itens_ctx = [
        SimpleNamespace(
            codigo=str(item.rubrica.codigo),
            nome=item.rubrica.nome,
            referencia=item.referencia or "-",
            provento=_fmt(item.valor_provento) if item.valor_provento else "",
            desconto=_fmt(item.valor_desconto) if item.valor_desconto else "",
        )
        for item in recibo.itens
    ]

    sf = resultado.get("salario_familia") or {}
    salario_familia_ctx = SimpleNamespace(
        elegivel=bool(sf.get("elegivel")),
        dependentes=(recibo.empregado.numero_dependentes_salario_familia if recibo.empregado else 0) or 0,
        valor_cota=_fmt(sf.get("valor_cota")),
        valor=_fmt(sf.get("valor")),
    )

    total_vencimentos = resultado["total_proventos"] + sf.get("valor", 0)
    total_descontos_com_tributos = (
        resultado["total_descontos"] + resultado["inss"]["valor"] + resultado["irrf"]["valor_final"]
    )

    return {
        "empresa": empresa_ctx,
        "beneficiario": beneficiario_ctx,
        "competencia_extenso": _competencia_extenso(recibo.competencia),
        "frase_quitacao": recibo.frase_quitacao.texto if recibo.frase_quitacao else FRASE_PADRAO,
        "itens": itens_ctx,
        "salario_familia": salario_familia_ctx,
        "total_vencimentos": _fmt(total_vencimentos),
        "total_descontos_com_tributos": _fmt(total_descontos_com_tributos),
        "liquido": _fmt(resultado["liquido"]),
        "inss_base": _fmt(resultado["base_inss"]),
        "inss_valor": _fmt(resultado["inss"]["valor"]),
        "irrf_base": _fmt(resultado["base_irrf"]),
        "irrf_valor": _fmt(resultado["irrf"]["valor_final"]),
        "irrf_aliquota": str(resultado["irrf"]["aliquota_faixa"]),
        "fgts_base": _fmt(resultado["base_fgts"]),
        "fgts_valor": _fmt(resultado["fgts"]),
    }


def gerar_recibo_docx(recibo, resultado) -> str:
    template = recibo.template_recibo or escolher_template_padrao(recibo.tipo)
    if not template:
        raise GeracaoReciboError(
            f'Nenhum modelo de recibo cadastrado para o tipo "{recibo.tipo}". '
            "Rode scripts/seed_templates_recibo.py."
        )

    caminho_template = os.path.join(DOCS_TEMPLATES_RECIBO_DIR, template.arquivo)
    if not os.path.exists(caminho_template):
        raise GeracaoReciboError(f"Arquivo de modelo não encontrado: {template.arquivo}")

    try:
        doc = DocxTemplate(caminho_template)
        doc.render(_montar_contexto(recibo, resultado))
    except Exception as exc:
        raise GeracaoReciboError(f"Falha ao preencher o modelo: {exc}") from exc

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nome_beneficiario = _slug(_nome_beneficiario(recibo))
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"recibo_{recibo.tipo}_{nome_beneficiario}_{recibo.competencia}_{carimbo}.docx"
    caminho = os.path.join(OUTPUT_DIR, nome_arquivo)
    doc.save(caminho)
    return caminho
