from datetime import datetime

from app.extensions import db


class ConfiguracaoManutencao(db.Model):
    """
    Registro único (id=1) que liga/desliga o modo manutenção do sistema.

    Editado só pela porta de administração (manutencao.py, processo
    separado na porta AXIOM_DP_PORT_MANUTENCAO — ver HANDOFF_CLAUDE_CODE.md,
    adendo B), lido pela porta principal (main.py) a cada requisição via
    `before_request`. Continua acessível mesmo se a porta principal cair
    durante uma atualização, por isso não fica só em memória.
    """

    __tablename__ = "configuracao_manutencao"

    id = db.Column(db.Integer, primary_key=True)
    ativo = db.Column(db.Boolean, default=False, nullable=False)
    titulo = db.Column(db.String(200), default="Sistema em manutenção")
    mensagem = db.Column(
        db.Text,
        default="Estamos atualizando o sistema. Voltamos em breve — obrigado pela paciência.",
    )
    previsao_retorno = db.Column(db.DateTime, nullable=True)
    atualizado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    atualizado_por = db.relationship("Usuario")

    @staticmethod
    def obter():
        """
        Sempre um único registro (id=1). Cria com valores padrão (modo
        manutenção desligado) na primeira vez que for consultado.
        """
        config = ConfiguracaoManutencao.query.get(1)
        if not config:
            config = ConfiguracaoManutencao(id=1, ativo=False)
            db.session.add(config)
            db.session.commit()
        return config
