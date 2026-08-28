"""
Serviço de consulta de dados públicos de CNPJ.

Provedor padrão: BrasilAPI (gratuita, sem chave).
Desenhado como adaptador para trocar de provedor no futuro
(ex.: ReceitaWS, CNPJ.ws) sem alterar quem consome este serviço.
"""
import requests

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


class CnpjConsultaError(Exception):
    pass


def _somente_digitos(cnpj: str) -> str:
    return "".join(ch for ch in cnpj if ch.isdigit())


def consultar_cnpj(cnpj: str) -> dict:
    """
    Consulta um CNPJ na BrasilAPI e devolve um dicionário já normalizado
    no formato usado pelo modelo Empresa. Lança CnpjConsultaError em
    caso de CNPJ inválido, não encontrado, ou falha de rede.
    """
    cnpj_limpo = _somente_digitos(cnpj)
    if len(cnpj_limpo) != 14:
        raise CnpjConsultaError("CNPJ deve conter 14 dígitos.")

    try:
        resp = requests.get(BRASILAPI_URL.format(cnpj=cnpj_limpo), timeout=10)
    except requests.RequestException as exc:
        raise CnpjConsultaError(f"Falha de conexão ao consultar CNPJ: {exc}") from exc

    if resp.status_code == 404:
        raise CnpjConsultaError("CNPJ não encontrado na base da Receita Federal.")
    if resp.status_code != 200:
        raise CnpjConsultaError(f"Erro ao consultar CNPJ (HTTP {resp.status_code}).")

    dados = resp.json()

    return {
        "razao_social": dados.get("razao_social"),
        "nome_fantasia": dados.get("nome_fantasia"),
        "cnpj": dados.get("cnpj"),
        "logradouro": dados.get("logradouro"),
        "numero": dados.get("numero"),
        "complemento": dados.get("complemento"),
        "bairro": dados.get("bairro"),
        "municipio": dados.get("municipio"),
        "uf": dados.get("uf"),
        "cep": dados.get("cep"),
        "cnae_principal": (dados.get("cnae_fiscal_descricao") or ""),
        "situacao_cadastral": dados.get("descricao_situacao_cadastral"),
        "data_abertura": dados.get("data_inicio_atividade"),
        "natureza_juridica": dados.get("natureza_juridica"),
    }
