"""
Correção de capitalização para dados vindos em CAIXA ALTA da Receita
Federal (planilhas do escritório e API da CNPJá seguem o mesmo padrão).

O dado bruto é sempre guardado como veio (auditoria/fidelidade) — este
utilitário só é aplicado na exibição e na geração de documentos, nunca
antes de salvar (ver HANDOFF_CLAUDE_CODE.md, seção 5.3).
"""
import re

CONECTORES = {"de", "da", "do", "das", "dos", "e"}

SIGLAS = {"LTDA", "ME", "EPP", "EIRELI", "S/A", "MEI", "EI"}

_RE_PONTUACAO_FINAL = re.compile(r"[.,;:]+$")


def _capitalizar_palavra(palavra: str) -> str:
    # Nomes compostos com hífen (ex.: "JOSE-CARLOS") capitalizam cada parte.
    return "-".join(
        (parte[:1].upper() + parte[1:].lower()) if parte else ""
        for parte in palavra.split("-")
    )


def titulo_pt(texto):
    """
    Aplica Title Case ao estilo pt-BR: conectores (de, da, do, dos, das, e)
    ficam em minúsculo — exceto se forem a primeira palavra — e siglas ou
    formas societárias (LTDA, ME, EPP, EIRELI, S/A, MEI, EI) ficam sempre
    maiúsculas. Aceita None (devolve None) para uso direto com campos
    opcionais.
    """
    if not texto:
        return texto

    palavras = texto.split()
    resultado = []
    for i, palavra in enumerate(palavras):
        chave = _RE_PONTUACAO_FINAL.sub("", palavra).upper()
        if chave in SIGLAS:
            resultado.append(palavra.upper())
        elif i > 0 and palavra.lower() in CONECTORES:
            resultado.append(palavra.lower())
        else:
            resultado.append(_capitalizar_palavra(palavra))

    return " ".join(resultado)
