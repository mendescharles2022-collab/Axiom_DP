"""
Motor de geração de documentos: pega um TemplateDocumento + uma Empresa +
(opcionalmente) um Empregado + um dicionário de campos extras, faz o merge
via docxtpl e salva o .docx final em documentos_gerados/.
"""
import json
import os
import re
import unicodedata
from datetime import date, datetime
from types import SimpleNamespace

from docxtpl import DocxTemplate

from app.config import DOCS_TEMPLATES_DIR, OUTPUT_DIR
from app.extensions import db
from app.models.emissao import DocumentoEmitido

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]


class GeracaoDocumentoError(Exception):
    pass


def _v(valor):
    """Nunca deixa None virar a string 'None' dentro do documento."""
    return "" if valor is None else valor


def _empresa_contexto(empresa):
    return SimpleNamespace(
        razao_social=_v(empresa.razao_social),
        nome_fantasia=_v(empresa.nome_fantasia),
        cnpj=_v(empresa.cnpj),
        inscricao_estadual=_v(empresa.inscricao_estadual),
        endereco_completo=empresa.endereco_completo() or "",
        municipio=_v(empresa.municipio),
        uf=_v(empresa.uf),
        cnae_principal=_v(empresa.cnae_principal),
        situacao_cadastral=_v(empresa.situacao_cadastral),
        natureza_juridica=_v(empresa.natureza_juridica),
    )


_CAMPOS_EMPREGADO_TEXTO = [
    "nome_completo", "cpf", "rg", "data_nascimento", "nacionalidade", "estado_civil",
    "ctps_numero", "ctps_serie", "pis_pasep", "endereco", "telefone", "email",
    "cargo", "setor", "tipo_contrato", "data_admissao", "data_desligamento",
    "banco", "agencia", "conta", "chave_pix",
]


def _empregado_contexto(empregado):
    if not empregado:
        return SimpleNamespace(**{c: "" for c in _CAMPOS_EMPREGADO_TEXTO}, salario_base="")
    dados = {c: _v(getattr(empregado, c)) for c in _CAMPOS_EMPREGADO_TEXTO}
    dados["salario_base"] = f"{empregado.salario_base:.2f}" if empregado.salario_base is not None else ""
    return SimpleNamespace(**dados)


def _slug_arquivo(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto or "documento"


def _contexto_data_emissao(data_emissao):
    if isinstance(data_emissao, str):
        data_emissao = datetime.strptime(data_emissao, "%Y-%m-%d").date()
    if not data_emissao:
        data_emissao = date.today()
    return {
        "data_emissao_dia": f"{data_emissao.day:02d}",
        "data_emissao_mes": MESES_PT[data_emissao.month - 1],
        "data_emissao_ano": str(data_emissao.year),
        "data_emissao_extenso": f"{data_emissao.day:02d} de {MESES_PT[data_emissao.month - 1]} de {data_emissao.year}",
    }


def gerar_documento(template, empresa, empregado, extra: dict, data_emissao=None, observacao: str = ""):
    """
    template: instância de TemplateDocumento
    empresa: instância de Empresa
    empregado: instância de Empregado ou None
    extra: dict com os campos extras específicos do documento
    data_emissao: date ou string 'AAAA-MM-DD' (default: hoje)
    """
    caminho_template = os.path.join(DOCS_TEMPLATES_DIR, template.arquivo)
    if not os.path.exists(caminho_template):
        raise GeracaoDocumentoError(f"Arquivo de template não encontrado: {template.arquivo}")

    try:
        doc = DocxTemplate(caminho_template)
    except Exception as exc:
        raise GeracaoDocumentoError(f"Falha ao abrir o template: {exc}") from exc

    campos_esperados = {c["nome"]: "" for c in template.campos_extra()}
    extra_completo = {**campos_esperados, **(extra or {})}
    extra_completo = {k: _v(v) for k, v in extra_completo.items()}

    contexto = {
        "empresa": _empresa_contexto(empresa),
        "empregado": _empregado_contexto(empregado),
        "extra": extra_completo,
        **_contexto_data_emissao(data_emissao),
    }

    try:
        doc.render(contexto)
    except Exception as exc:
        raise GeracaoDocumentoError(f"Falha ao preencher o modelo: {exc}") from exc

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    nome_empregado = _slug_arquivo(empregado.nome_completo) if empregado else "geral"
    nome_template = _slug_arquivo(template.nome)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome_template}_{nome_empregado}_{carimbo}.docx"
    caminho_saida = os.path.join(OUTPUT_DIR, nome_arquivo)
    doc.save(caminho_saida)

    registro = DocumentoEmitido(
        template_id=template.id,
        empresa_id=empresa.id,
        empregado_id=empregado.id if empregado else None,
        caminho_arquivo_gerado=caminho_saida,
        dados_utilizados_json=json.dumps(extra_completo, ensure_ascii=False, default=str),
        observacao=observacao,
    )
    db.session.add(registro)
    db.session.commit()

    return caminho_saida, registro
