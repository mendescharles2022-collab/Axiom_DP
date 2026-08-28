"""
Axiom_DP — ponto de entrada.

Sobe o servidor Flask localmente (127.0.0.1) em uma thread separada e
abre uma janela nativa do sistema operacional com pywebview apontando
para ele. O usuário nunca vê barra de endereço nem "cara de navegador"
— é uma janela de programa como qualquer outra.
"""
import threading
import webview
from app import create_app

HOST = "127.0.0.1"
PORT = 5151


def rodar_flask():
    app = create_app()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def main():
    thread_flask = threading.Thread(target=rodar_flask, daemon=True)
    thread_flask.start()

    webview.create_window(
        "Axiom_DP — Departamento Pessoal",
        f"http://{HOST}:{PORT}",
        width=1100,
        height=750,
        min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
