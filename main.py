"""
Axiom_DP — ponto de entrada.

`python main.py` sobe o sistema completo — porta principal
(AXIOM_DP_PORT, padrão 5600) — escutando em todas as interfaces de
rede (0.0.0.0), para ser acessado pelo navegador de qualquer estação
do escritório, inclusive a própria máquina que hospeda. Não é mais um
app desktop isolado por máquina (ver HANDOFF_CLAUDE_CODE.md, seção 3).

Também garante que a porta de administração/manutenção
(AXIOM_DP_PORT_MANUTENCAO, padrão 5601, ver manutencao.py) esteja no
ar, subindo-a se ainda não estiver — mas como processo do sistema
operacional **desacoplado** deste, não um processo filho preso ao
ciclo de vida dele. Por isso um Ctrl+C ou a queda/reinício da porta
principal durante uma atualização não derruba a de manutenção junto
(HANDOFF_CLAUDE_CODE.md, adendo B). Se precisar subir só uma das duas
isoladamente, rode `python manutencao.py` direto.
"""
import os
import socket
import subprocess
import sys

from app import create_app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = "0.0.0.0"
PORT = int(os.environ.get("AXIOM_DP_PORT", "5600"))
PORT_MANUTENCAO = int(os.environ.get("AXIOM_DP_PORT_MANUTENCAO", "5601"))


def _porta_ja_em_uso(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", porta))
            return True
        except OSError:
            return False


def _subir_manutencao_desacoplada():
    if _porta_ja_em_uso(PORT_MANUTENCAO):
        return

    caminho_script = os.path.join(BASE_DIR, "manutencao.py")
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, caminho_script], **kwargs)


def main():
    _subir_manutencao_desacoplada()
    app = create_app()
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
