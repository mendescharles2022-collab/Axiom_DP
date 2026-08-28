"""
Popula a tabela templates_documentos a partir de app/docs_templates/catalogo.json
(gerado por converter_templates_docxtpl.py). Pode ser rodado quantas vezes
for preciso — atualiza os existentes (por caminho de arquivo) e cria os novos.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.documento import TemplateDocumento
from app.config import DOCS_TEMPLATES_DIR

CATEGORIAS_LEGIVEIS = {
    "01-Avisos-Previos": "Avisos Prévios",
    "02-Contratos-de-Trabalho": "Contratos de Trabalho",
    "03-Declaracoes": "Declarações",
    "04-Advertencias-e-Suspensoes": "Advertências e Suspensões",
    "05-Cartas-de-Recomendacao": "Cartas de Recomendação",
    "06-Admissao-e-Registro-Funcional": "Admissão e Registro Funcional",
    "07-Contratos-Especiais-e-Aditivos": "Contratos Especiais e Aditivos",
    "08-Ferias-e-Afastamentos": "Férias e Afastamentos",
    "09-Rescisao-e-Desligamento": "Rescisão e Desligamento",
}


def main():
    catalogo_path = os.path.join(DOCS_TEMPLATES_DIR, "catalogo.json")
    with open(catalogo_path, encoding="utf-8") as f:
        catalogo = json.load(f)

    app = create_app()
    with app.app_context():
        criados, atualizados = 0, 0
        for item in catalogo:
            categoria_legivel = CATEGORIAS_LEGIVEIS.get(item["categoria"], item["categoria"])
            existente = TemplateDocumento.query.filter_by(arquivo=item["arquivo"]).first()
            variaveis_json = json.dumps(item["campos_extras"], ensure_ascii=False)

            if existente:
                existente.categoria = categoria_legivel
                existente.nome = item["nome"].strip().title()
                existente.variaveis_extra_json = variaveis_json
                atualizados += 1
            else:
                novo = TemplateDocumento(
                    categoria=categoria_legivel,
                    nome=item["nome"].strip().title(),
                    arquivo=item["arquivo"],
                    variaveis_extra_json=variaveis_json,
                )
                db.session.add(novo)
                criados += 1

        db.session.commit()
        print(f"Templates criados: {criados} | atualizados: {atualizados}")


if __name__ == "__main__":
    main()
