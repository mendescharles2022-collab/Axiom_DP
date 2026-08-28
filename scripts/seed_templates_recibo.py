"""
Popula o catálogo de modelos de recibo avulso (TemplateRecibo) a partir
dos .docx gerados em app/docs_templates_recibo/ por
scripts/gerar_templates_recibo.py. Idempotente por arquivo — pode ser
rodado de novo sem duplicar.

Uso: python scripts/seed_templates_recibo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.template_recibo import TemplateRecibo

MODELOS = [
    ("contracheque", "Clássico (2 vias)", "contracheque_classico.docx"),
    ("contracheque", "Moderno", "contracheque_moderno.docx"),
    ("pro_labore", "Clássico (2 vias)", "pro_labore_classico.docx"),
    ("pro_labore", "Moderno", "pro_labore_moderno.docx"),
]


def seed():
    criados, atualizados = 0, 0
    for tipo, nome, arquivo in MODELOS:
        existente = TemplateRecibo.query.filter_by(arquivo=arquivo).first()
        if existente:
            existente.tipo = tipo
            existente.nome = nome
            existente.ativo = True
            atualizados += 1
        else:
            db.session.add(TemplateRecibo(tipo=tipo, nome=nome, arquivo=arquivo, ativo=True))
            criados += 1
    db.session.commit()
    print(f"TemplateRecibo — criados: {criados} | atualizados: {atualizados}")


def main():
    app = create_app()
    with app.app_context():
        seed()


if __name__ == "__main__":
    main()
