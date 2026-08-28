"""
Converte os modelos .docx do pacote de DP (placeholders em colchetes)
para o formato docxtpl (variáveis Jinja {{ }}), mapeando automaticamente
para os campos de Empresa/Empregado quando possível, e gerando um
"campo extra" nomeado (com rótulo legível) para tudo o que não tem
correspondência direta no cadastro.

Uso: python scripts/converter_templates_docxtpl.py
Gera: um manifesto JSON por template em app/docs_templates/<mesmo caminho>.campos.json
      e um catálogo consolidado em app/docs_templates/catalogo.json
"""
import glob
import json
import os
import re
import unicodedata

import docx

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "docs_templates")

# Substituições exatas, processadas na ordem (mais específicas primeiro).
TOKEN_MAP = [
    ("[RAZÃO SOCIAL DA TOMADORA], CNPJ [00.000.000/0000-00]",
     "{{ extra.razao_social_tomadora }}, CNPJ {{ extra.cnpj_tomadora }}"),
    ("[endereço completo, cidade/UF]",
     "{{ empresa.endereco_completo }}, {{ empresa.municipio }}/{{ empresa.uf }}"),
    ("[Cidade] – [UF], [DD] de [mês] de [AAAA].",
     "{{ empresa.municipio }} – {{ empresa.uf }}, {{ data_emissao_extenso }}."),
    ("CNPJ [00.000.000/0000-00]  ·  [Endereço completo]  ·  [Cidade/UF]",
     "CNPJ {{ empresa.cnpj }}  ·  {{ empresa.endereco_completo }}  ·  {{ empresa.municipio }}/{{ empresa.uf }}"),
    ("[Endereço completo]", "{{ empresa.endereco_completo }}"),
    ("[endereço completo]", "{{ empregado.endereco }}"),
    ("[RAZÃO SOCIAL DA EMPRESA]", "{{ empresa.razao_social }}"),
    ("[00.000.000/0000-00]", "{{ empresa.cnpj }}"),
    ("[Cidade/UF]", "{{ empresa.municipio }}/{{ empresa.uf }}"),
    ("[CIDADE/UF]", "{{ empresa.municipio }}/{{ empresa.uf }}"),
    ("[Cidade]", "{{ empresa.municipio }}"),
    ("[UF]", "{{ empresa.uf }}"),
    ("[LOGOMARCA DA EMPRESA]", ""),
    ("[NOME COMPLETO DO EMPREGADO]", "{{ empregado.nome_completo }}"),
    ("[NOME DO EMPREGADO]", "{{ empregado.nome_completo }}"),
    ("[NOME COMPLETO]", "{{ empregado.nome_completo }}"),
    ("[000.000.000-00]", "{{ empregado.cpf }}"),
    ("[CARGO/FUNÇÃO]", "{{ empregado.cargo }}"),
    ("[SETOR]", "{{ empregado.setor }}"),
    ("[nacionalidade]", "{{ empregado.nacionalidade }}"),
    ("[DD]", "{{ data_emissao_dia }}"),
    ("[mês]", "{{ data_emissao_mes }}"),
    ("[AAAA]", "{{ data_emissao_ano }}"),
    ("[NOME DO RESPONSÁVEL]", "{{ extra.nome_responsavel }}"),
]

# Rótulos de linhas de tabela (coluna 1) que mapeiam direto para um campo
# já cadastrado, quando a coluna 2 ainda tiver colchete após o TOKEN_MAP.
_LABEL_MAP_RAW = {
    "cargo/função": "{{ empregado.cargo }}",
    "cargo": "{{ empregado.cargo }}",
    "cargo/função de destino": "{{ empregado.cargo }}",
    "nome do empregado": "{{ empregado.nome_completo }}",
    "nome completo": "{{ empregado.nome_completo }}",
    "cpf": "{{ empregado.cpf }}",
    "setor/departamento": "{{ empregado.setor }}",
    "setor": "{{ empregado.setor }}",
    "data de admissão": "{{ empregado.data_admissao }}",
    "data de admissão original": "{{ empregado.data_admissao }}",
    "salário-base": "{{ empregado.salario_base }}",
    "banco": "{{ empregado.banco }}",
    "agência": "{{ empregado.agencia }}",
    "conta": "{{ empregado.conta }}",
    "tipo de chave pix (se houver)": "{{ empregado.chave_pix }}",
    "data de nascimento": "{{ empregado.data_nascimento }}",
    "nacionalidade": "{{ empregado.nacionalidade }}",
    "estado civil": "{{ empregado.estado_civil }}",
    "rg / órgão emissor": "{{ empregado.rg }}",
    "pis/pasep/nit": "{{ empregado.pis_pasep }}",
    "endereço completo": "{{ empregado.endereco }}",
    "telefone": "{{ empregado.telefone }}",
    "e-mail": "{{ empregado.email }}",
    "tipo de contrato": "{{ empregado.tipo_contrato }}",
}

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
            "agosto", "setembro", "outubro", "novembro", "dezembro"]


def slugify(texto: str) -> str:
    texto = texto.strip().rstrip(":").lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "campo"


LABEL_MAP = {slugify(k): v for k, v in _LABEL_MAP_RAW.items()}


def aplicar_token_map(texto: str) -> str:
    for origem, destino in TOKEN_MAP:
        if origem in texto:
            texto = texto.replace(origem, destino)
    return texto


def processar_runs_do_paragrafo(paragrafo):
    for run in paragrafo.runs:
        if "[" in run.text:
            run.text = aplicar_token_map(run.text)


def iterar_paragrafos(doc):
    for p in doc.paragraphs:
        yield p
    for tabela in doc.tables:
        for row in tabela.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield p
    for secao in doc.sections:
        for p in secao.header.paragraphs:
            yield p
        for p in secao.footer.paragraphs:
            yield p


def contexto_anterior(texto: str, pos: int) -> str:
    """Pega as últimas palavras antes do colchete (até a pontuação anterior),
    para nomear o campo com base no contexto real da frase."""
    trecho = texto[:pos]
    trecho = re.split(r"[.;,:]", trecho)[-1].strip()
    palavras = trecho.split()[-4:]
    return " ".join(palavras)


STOPWORDS_BORDA = {"de", "da", "do", "das", "dos", "em", "no", "na", "sob", "o", "a",
                    "e", "ou", "nº", "n", "por", "ao", "à", "com"}


def nome_a_partir_do_contexto(texto_antes: str) -> str:
    slug = slugify(texto_antes)
    partes = [p for p in slug.split("_") if p and p not in STOPWORDS_BORDA]
    return "_".join(partes)[:40]


def processar_tabelas_com_label(doc, manifesto, contador):
    """Para cada linha de tabela (rótulo + valor), tenta mapear o valor
    inteiro para um campo direto quando ele é UM ÚNICO colchete e o rótulo
    é conhecido. Caso contrário, delega ao processamento genérico por
    colchete (que preserva o que já foi resolvido pelo TOKEN_MAP)."""
    padrao_unico = re.compile(r"^\[[^\[\]]{1,80}\]$")

    for tabela in doc.tables:
        for row in tabela.rows:
            if len(row.cells) != 2:
                continue
            label_texto = row.cells[0].text.strip()
            slug_label = slugify(label_texto)
            cell_valor = row.cells[1]

            for p in cell_valor.paragraphs:
                for run in p.runs:
                    if "[" not in run.text:
                        continue

                    # Caso simples: a célula inteira é só um colchete -> usa o rótulo da linha
                    if padrao_unico.fullmatch(run.text.strip()):
                        tag_direta = LABEL_MAP.get(slug_label)
                        if tag_direta:
                            run.text = tag_direta
                            continue
                        nome_campo = _registrar_campo(manifesto, contador, slug_label, label_texto)
                        run.text = f"{{{{ extra.{nome_campo} }}}}"
                        continue

                    # Caso composto: múltiplos colchetes/frase — nomeia por contexto
                    run.text = _substituir_por_contexto(run.text, manifesto, contador, rotulo_linha=label_texto)


def _identificador_valido(nome: str) -> str:
    """Jinja/Python não aceitam identificador começando com dígito."""
    if nome and nome[0].isdigit():
        return f"campo_{nome}"
    return nome


def _registrar_campo(manifesto, contador, nome_base, rotulo):
    nome_base = _identificador_valido(nome_base)
    nome_campo = nome_base if nome_base not in manifesto["usados"] else None
    if not nome_campo:
        contador["n"] += 1
        nome_campo = f"{nome_base}_{contador['n']}"
    manifesto["usados"].add(nome_campo)

    contagem_rotulo = manifesto["rotulos_contagem"].get(rotulo, 0) + 1
    manifesto["rotulos_contagem"][rotulo] = contagem_rotulo
    rotulo_exibido = f"{rotulo} (parte {contagem_rotulo})" if contagem_rotulo > 1 else rotulo

    manifesto["campos"].append({"nome": nome_campo, "rotulo": rotulo_exibido, "tipo": "texto"})
    return nome_campo


CONTEXT_FIELD_ALIASES = {
    "nacionalidade": "{{ empregado.nacionalidade }}",
    "estado_civil": "{{ empregado.estado_civil }}",
    "salario_base": "{{ empregado.salario_base }}",
    "salario": "{{ empregado.salario_base }}",
    "banco": "{{ empregado.banco }}",
    "agencia": "{{ empregado.agencia }}",
    "conta": "{{ empregado.conta }}",
    "telefone": "{{ empregado.telefone }}",
    "email": "{{ empregado.email }}",
    "cargo": "{{ empregado.cargo }}",
    "setor": "{{ empregado.setor }}",
    "cnpj": "{{ empresa.cnpj }}",
    "razao_social": "{{ empresa.razao_social }}",
    "cpf": "{{ empregado.cpf }}",
    "rg": "{{ empregado.rg }}",
    "pis": "{{ empregado.pis_pasep }}",
    "carteira_trabalho": "{{ empregado.ctps_numero }}",
    "trabalho_serie": "{{ empregado.ctps_serie }}",
    "data_nascimento": "{{ empregado.data_nascimento }}",
    "data_admissao": "{{ empregado.data_admissao }}",
}


NOMES_FRACOS = {"r", "rs", "r_", "n", "no", "num", "numero", "valor"}


def _substituir_por_contexto(texto: str, manifesto, contador, rotulo_linha: str = "") -> str:
    padrao = re.compile(r"\[[^\[\]]{1,400}\]")
    ocorrencia = {"i": 0}

    def substituto(m):
        contexto = contexto_anterior(texto, m.start())
        base = nome_a_partir_do_contexto(contexto) or slugify(m.group(0)[1:-1])[:40]
        if base in CONTEXT_FIELD_ALIASES:
            return CONTEXT_FIELD_ALIASES[base]
        if (not base or base in NOMES_FRACOS) and rotulo_linha:
            base = nome_a_partir_do_contexto(rotulo_linha) or slugify(rotulo_linha)
            ocorrencia["i"] += 1
            if ocorrencia["i"] > 1:
                base = f"{base}_{ocorrencia['i']}"
        if not base:
            contador["n"] += 1
            base = f"campo_{contador['n']}"
        rotulo = rotulo_linha or contexto or m.group(0)[1:-1]
        nome_campo = _registrar_campo(manifesto, contador, base, rotulo.capitalize())
        return f"{{{{ extra.{nome_campo} }}}}"

    return padrao.sub(substituto, texto)


def processar_sobras_genericas(doc, manifesto, contador):
    for p in iterar_paragrafos(doc):
        for run in p.runs:
            if "[" not in run.text:
                continue
            run.text = _substituir_por_contexto(run.text, manifesto, contador)


# Correções pontuais para casos em que o mesmo texto de origem tem
# significados diferentes em documentos diferentes (detectados em testes).
CORRECOES_POR_ARQUIVO = {
    "09-Rescisao-e-Desligamento/05-Recibo_de_Pagamento_de_Verbas.docx": [
        ("com domicílio à {{ empregado.endereco }}", "com domicílio à {{ empresa.endereco_completo }}"),
    ],
}


def aplicar_correcoes_conhecidas(doc, caminho_relativo):
    pares = CORRECOES_POR_ARQUIVO.get(caminho_relativo)
    if not pares:
        return
    for p in iterar_paragrafos(doc):
        for run in p.runs:
            for origem, destino in pares:
                if origem in run.text:
                    run.text = run.text.replace(origem, destino)


def converter_arquivo(caminho):
    doc = docx.Document(caminho)
    manifesto = {"arquivo": os.path.relpath(caminho, TEMPLATES_DIR), "campos": [], "usados": set(), "rotulos_contagem": {}}
    contador = {"n": 0}

    # 1) Substituições diretas conhecidas em qualquer parágrafo/célula
    for p in iterar_paragrafos(doc):
        processar_runs_do_paragrafo(p)

    # 2) Linhas de tabela com rótulo -> campo direto ou campo extra nomeado
    processar_tabelas_com_label(doc, manifesto, contador)

    # 3) Qualquer colchete restante (fora de tabelas) vira campo extra genérico
    processar_sobras_genericas(doc, manifesto, contador)

    # 4) Correções pontuais conhecidas (ambiguidades específicas de um arquivo)
    aplicar_correcoes_conhecidas(doc, manifesto["arquivo"])

    doc.save(caminho)

    # Verificação de integridade: não pode sobrar nenhum colchete
    doc_verificacao = docx.Document(caminho)
    restante = []
    for p in iterar_paragrafos(doc_verificacao):
        for r in p.runs:
            if "[" in r.text:
                restante.append(r.text)

    manifesto["campos_extras_total"] = len(manifesto["campos"])
    del manifesto["usados"]
    del manifesto["rotulos_contagem"]
    return manifesto, restante


def main():
    arquivos = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "**", "*.docx"), recursive=True))
    catalogo = []
    problemas = {}

    for caminho in arquivos:
        manifesto, restante = converter_arquivo(caminho)
        if restante:
            problemas[manifesto["arquivo"]] = restante

        categoria = os.path.basename(os.path.dirname(caminho))
        nome = os.path.splitext(os.path.basename(caminho))[0]
        nome_legivel = re.sub(r"^\d+-", "", nome).replace("_", " ")

        manifesto_path = caminho + ".campos.json"
        with open(manifesto_path, "w", encoding="utf-8") as f:
            json.dump(manifesto["campos"], f, ensure_ascii=False, indent=2)

        catalogo.append({
            "categoria": categoria,
            "nome": nome_legivel,
            "arquivo": manifesto["arquivo"],
            "campos_extras": manifesto["campos"],
        })

    with open(os.path.join(TEMPLATES_DIR, "catalogo.json"), "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    print(f"Convertidos {len(arquivos)} modelos.")
    total_extras = sum(len(c["campos_extras"]) for c in catalogo)
    print(f"Total de campos extras identificados: {total_extras}")
    if problemas:
        print("\nATENÇÃO — sobrou colchete não convertido em:")
        for arq, sobras in problemas.items():
            print(f"  {arq}: {sobras}")
    else:
        print("Verificação OK: nenhum colchete restante em nenhum template.")


if __name__ == "__main__":
    main()
