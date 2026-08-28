"""
Semeia a frase de quitação tradicional (HANDOFF seção 5.6) — a segunda
frase, com o texto exigido por um cliente específico do Charles, entra
depois pela tela de administração (Frases de quitação) quando ele
enviar o texto.

Uso: python scripts/seed_frase_quitacao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.frase_quitacao import FraseQuitacao

NOME_TRADICIONAL = "Tradicional"
TEXTO_TRADICIONAL = (
    "Declaro que recebi o valor descrito e dou plena quitação do que me é devido até o momento."
)


def seed():
    if FraseQuitacao.query.filter_by(nome=NOME_TRADICIONAL).first():
        print("Frase 'Tradicional' já existe.")
        return
    db.session.add(FraseQuitacao(nome=NOME_TRADICIONAL, texto=TEXTO_TRADICIONAL))
    db.session.commit()
    print("Frase 'Tradicional' criada.")


def main():
    app = create_app()
    with app.app_context():
        seed()


if __name__ == "__main__":
    main()
