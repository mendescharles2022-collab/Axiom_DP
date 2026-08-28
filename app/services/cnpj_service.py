"""
Serviço de consulta de dados públicos de CNPJ.

Provedor: CNPJá (endpoint público open.cnpja.com, sem necessidade de
cadastro/chave). Trocado a partir da BrasilAPI porque devolve muito mais
dado útil para o cadastro: CNAEs secundários, quadro societário (QSA),
inscrições estaduais por UF, SUFRAMA, opção pelo Simples/MEI com datas,
situação especial (recuperação judicial, falência), capital social, porte,
telefone e e-mail (ver HANDOFF_CLAUDE_CODE.md, seção 4).

Limite gratuito: 5 requisições/minuto por IP — adequado para consulta
interativa de escritório, não para lote.

IMPORTANTE: o mapeamento de campos abaixo foi feito a partir da
documentação pública da CNPJá, mas não pôde ser validado aqui contra uma
chamada real (o ambiente de desenvolvimento não tem saída de rede para
open.cnpja.com). Antes de depender deste serviço em produção, faça uma
consulta real e confira principalmente os campos de members/QSA,
registrations/IE e situação especial — ajuste os nomes de chave em
`_mapear_resposta` se necessário. O restante do sistema depende apenas da
assinatura pública (`consultar_cnpj`, `CnpjConsultaError`), então um ajuste
aqui não deve exigir mudanças em quem consome este serviço.
"""
import re

import requests

CNPJA_URL = "https://open.cnpja.com/office/{doc}"

# CNPJ alfanumérico (Lei/IN RFB 2.229/2024, vigente desde 31/07/2026):
# as 12 primeiras posições aceitam A-Z e 0-9; os 2 dígitos verificadores
# finais continuam sempre numéricos. CNPJs antigos (só números) continuam
# válidos e coexistem.
_RE_CNPJ_ALFANUMERICO = re.compile(r"^[A-Z0-9]{12}\d{2}$")


class CnpjConsultaError(Exception):
    pass


def _normalizar_cnpj(cnpj: str) -> str:
    """Remove máscara e uppercasa; NÃO usar \\d puro — CNPJ pode ser alfanumérico."""
    limpo = re.sub(r"[^0-9A-Za-z]", "", cnpj or "").upper()
    return limpo


def _v(dados: dict, *caminho, default=None):
    """Navega um dict aninhado com segurança: _v(dados, 'company', 'name')."""
    atual = dados
    for chave in caminho:
        if not isinstance(atual, dict):
            return default
        atual = atual.get(chave)
    return atual if atual is not None else default


def _mapear_resposta(dados: dict) -> dict:
    endereco = dados.get("address") or {}
    empresa = dados.get("company") or {}
    atividade_principal = dados.get("mainActivity") or {}
    atividades_secundarias = dados.get("sideActivities") or []
    situacao = dados.get("status") or {}
    situacao_especial = dados.get("specialSituation") or {}
    simples = _v(empresa, "simples", default={}) or {}
    simei = _v(empresa, "simei", default={}) or {}
    natureza = _v(empresa, "nature", default={}) or {}
    porte = _v(empresa, "size", default={}) or {}

    telefones = dados.get("phones") or []
    emails = dados.get("emails") or []
    telefone = None
    if telefones:
        t = telefones[0]
        ddd = t.get("area", "")
        numero = t.get("number", "")
        telefone = f"({ddd}) {numero}" if ddd else numero
    email = emails[0].get("address") if emails else None

    socios = []
    for membro in _v(empresa, "members", default=[]) or []:
        pessoa = membro.get("person") or {}
        socios.append({
            "nome": pessoa.get("name"),
            "qualificacao": _v(membro, "role", "text"),
            "cpf_parcial": pessoa.get("taxId"),
        })

    cnaes_secundarios = [
        {"codigo": str(a.get("id") or ""), "descricao": a.get("text")}
        for a in atividades_secundarias
    ]

    inscricoes_estaduais = [
        {
            "uf": r.get("state"),
            "numero": r.get("number"),
            "situacao": _v(r, "status", "text"),
        }
        for r in (dados.get("registrations") or [])
    ]

    return {
        "razao_social": empresa.get("name") or dados.get("company", {}).get("name"),
        "nome_fantasia": dados.get("alias"),
        "cnpj": dados.get("taxId"),
        "logradouro": endereco.get("street"),
        "numero": endereco.get("number"),
        "complemento": endereco.get("details"),
        "bairro": endereco.get("district"),
        "municipio": endereco.get("city"),
        "uf": endereco.get("state"),
        "cep": endereco.get("zip"),
        "cnae_principal": atividade_principal.get("text"),
        "situacao_cadastral": situacao.get("text"),
        "data_abertura": dados.get("founded"),
        "data_fundacao": dados.get("founded"),
        "natureza_juridica": natureza.get("text"),
        "porte": porte.get("text"),
        "capital_social": empresa.get("equity"),
        "situacao_especial": situacao_especial.get("text"),
        "data_situacao_especial": situacao_especial.get("date"),
        "telefone_rfb": telefone,
        "email_rfb": email,
        "opcao_simples": bool(simples.get("optant")),
        "data_opcao_simples": simples.get("since"),
        "opcao_mei": bool(simei.get("optant")),
        "data_opcao_mei": simei.get("since"),
        "cnaes_secundarios": cnaes_secundarios,
        "socios": socios,
        "inscricoes_estaduais": inscricoes_estaduais,
    }


def consultar_cnpj(cnpj: str) -> dict:
    """
    Consulta um CNPJ na CNPJá e devolve um dicionário já normalizado no
    formato usado pelo modelo Empresa (inclui listas cnaes_secundarios,
    socios e inscricoes_estaduais para as tabelas relacionadas). Lança
    CnpjConsultaError em caso de CNPJ inválido, não encontrado, limite de
    requisições excedido, ou falha de rede.
    """
    doc = _normalizar_cnpj(cnpj)
    if not _RE_CNPJ_ALFANUMERICO.match(doc):
        raise CnpjConsultaError("CNPJ deve conter 14 posições (12 alfanuméricas + 2 dígitos verificadores numéricos).")

    try:
        resp = requests.get(CNPJA_URL.format(doc=doc), timeout=10)
    except requests.RequestException as exc:
        raise CnpjConsultaError(f"Falha de conexão ao consultar CNPJ: {exc}") from exc

    if resp.status_code == 404:
        raise CnpjConsultaError("CNPJ não encontrado na base da Receita Federal.")
    if resp.status_code == 429:
        raise CnpjConsultaError("Limite de consultas à CNPJá excedido (5/minuto). Aguarde um instante e tente novamente.")
    if resp.status_code != 200:
        raise CnpjConsultaError(f"Erro ao consultar CNPJ (HTTP {resp.status_code}).")

    try:
        dados = resp.json()
    except ValueError as exc:
        raise CnpjConsultaError("Resposta inválida da CNPJá.") from exc

    return _mapear_resposta(dados)
