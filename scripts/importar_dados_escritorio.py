"""
Importa os dados fornecidos pelo escritório (HANDOFF_CLAUDE_CODE.md, seção 7):

- dados_para_importar/Relação_de_Empresas_-.xlsx -> Empresa
  (537 clientes: 491 com CNPJ, 46 com CPF — campos básicos apenas; os
  campos que só a CNPJá preenche ficam vazios até o usuário clicar em
  "Atualizar dados da Receita" empresa por empresa).
- dados_para_importar/RELAÇÃO_DE_RUBRICA.xls -> Rubrica
  (1.798 rubricas, catálogo global).

Idempotente: pode ser rodado de novo sem duplicar — casa empresas pelo
documento (dígitos do CNPJ/CPF) e rubricas pelo código.

Uso: python scripts/importar_dados_escritorio.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
import xlrd

from app import create_app
from app.extensions import db
from app.models.empresa import Empresa
from app.models.rubrica import Rubrica

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANILHA_EMPRESAS = os.path.join(RAIZ, "dados_para_importar", "Relação_de_Empresas_-.xlsx")
PLANILHA_RUBRICAS = os.path.join(RAIZ, "dados_para_importar", "RELAÇÃO_DE_RUBRICA.xls")


def _somente_digitos(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _formatar_documento(digitos: str, tipo: str) -> str:
    if tipo == "CPF":
        digitos = digitos.zfill(11)
        return f"{digitos[0:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"
    digitos = digitos.zfill(14)
    return f"{digitos[0:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"


def importar_empresas(caminho=PLANILHA_EMPRESAS):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.active

    existentes = {_somente_digitos(e.cnpj): e for e in Empresa.query.all()}

    criadas, atualizadas, ignoradas = 0, 0, 0
    cabecalho_encontrado = False
    for row in ws.iter_rows(values_only=True):
        razao_social, tipo_inscricao, inscricao, status, forma_envio = row[1:6]

        if razao_social == "Razão Social":
            cabecalho_encontrado = True
            continue
        if not cabecalho_encontrado or not razao_social or not tipo_inscricao:
            continue

        digitos = _somente_digitos(inscricao)
        if not digitos:
            ignoradas += 1
            continue
        # Zera à esquerda ANTES de usar como chave de correspondência —
        # a célula da planilha pode vir sem o zero (ex.: CPF "438290151"),
        # mas o valor já salvo no banco tem o documento completo
        # formatado; sem este padding, a mesma empresa reimportada não
        # bate com o registro existente e a reimportação duplica o CNPJ.
        digitos = digitos.zfill(11 if tipo_inscricao == "CPF" else 14)

        documento = _formatar_documento(digitos, tipo_inscricao)
        status = status if status in ("Ativo", "Inativo") else "Ativo"
        forma_envio = forma_envio if forma_envio and forma_envio != "-" else None

        empresa = existentes.get(digitos)
        if empresa:
            empresa.razao_social = str(razao_social).strip()
            empresa.tipo_inscricao = tipo_inscricao
            empresa.status = status
            empresa.forma_envio = forma_envio
            atualizadas += 1
        else:
            empresa = Empresa(
                razao_social=str(razao_social).strip(),
                tipo_inscricao=tipo_inscricao,
                cnpj=documento,
                status=status,
                forma_envio=forma_envio,
            )
            db.session.add(empresa)
            existentes[digitos] = empresa
            criadas += 1

    db.session.commit()
    print(f"Empresas — criadas: {criadas} | atualizadas: {atualizadas} | ignoradas (sem inscrição): {ignoradas}")
    return criadas, atualizadas, ignoradas


def _valor_incidencia(valor):
    if valor in (None, ""):
        return None
    return int(valor)


def importar_rubricas(caminho=PLANILHA_RUBRICAS):
    wb = xlrd.open_workbook(caminho)
    sh = wb.sheet_by_index(0)

    existentes = {r.codigo: r for r in Rubrica.query.all()}

    criadas, atualizadas = 0, 0
    for i in range(1, sh.nrows):
        linha = sh.row_values(i)
        codigo_bruto = linha[0]
        if not codigo_bruto or not isinstance(codigo_bruto, float):
            continue  # pula a linha de rodapé ("Total de itens listados: ...")

        codigo = int(codigo_bruto)
        nome = str(linha[5]).strip()
        tipo = str(linha[10]).strip()
        incidencia_irrf = _valor_incidencia(linha[12])
        incidencia_inss = _valor_incidencia(linha[14])
        incidencia_fgts = _valor_incidencia(linha[16])
        incidencia_pis = _valor_incidencia(linha[19])

        rubrica = existentes.get(codigo)
        if rubrica:
            rubrica.nome = nome
            rubrica.tipo = tipo
            rubrica.incidencia_irrf = incidencia_irrf
            rubrica.incidencia_inss = incidencia_inss
            rubrica.incidencia_fgts = incidencia_fgts
            rubrica.incidencia_pis = incidencia_pis
            atualizadas += 1
        else:
            rubrica = Rubrica(
                codigo=codigo,
                nome=nome,
                tipo=tipo,
                incidencia_irrf=incidencia_irrf,
                incidencia_inss=incidencia_inss,
                incidencia_fgts=incidencia_fgts,
                incidencia_pis=incidencia_pis,
            )
            db.session.add(rubrica)
            existentes[codigo] = rubrica
            criadas += 1

    db.session.commit()
    print(f"Rubricas — criadas: {criadas} | atualizadas: {atualizadas}")
    return criadas, atualizadas


def main():
    app = create_app()
    with app.app_context():
        importar_empresas()
        importar_rubricas()


if __name__ == "__main__":
    main()
