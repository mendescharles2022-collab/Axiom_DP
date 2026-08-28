"""
Axiom_DP — ponto de entrada.

Sobe o servidor Flask escutando em todas as interfaces de rede
(0.0.0.0), para ser acessado pelo navegador de qualquer estação do
escritório — inclusive a própria máquina que hospeda. Não é mais um
app desktop isolado por máquina (ver HANDOFF_CLAUDE_CODE.md, seção 3).
"""
import os

from app import create_app

HOST = "0.0.0.0"
PORT = int(os.environ.get("AXIOM_DP_PORT", "5151"))


def main():
    app = create_app()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
