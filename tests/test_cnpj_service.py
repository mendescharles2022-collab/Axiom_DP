import pytest

from app.services.cnpj_service import CnpjConsultaError, _mapear_resposta, consultar_cnpj

AMOSTRA_CNPJA = {
    "updated": "2026-06-25T02:14:44.000Z",
    "taxId": "11222333000181",
    "alias": "Empresa Fantasia",
    "founded": "2010-05-25",
    "head": True,
    "statusDate": "2010-05-25",
    "status": {"id": 2, "text": "Ativa"},
    "specialSituation": {"text": None, "date": None},
    "address": {
        "municipality": 5208707,
        "street": "Rua das Flores",
        "number": "100",
        "details": "Sala 2",
        "district": "Centro",
        "city": "Itapaci",
        "state": "GO",
        "zip": "76490000",
        "country": {"id": 76, "name": "Brasil"},
    },
    "phones": [{"type": "LANDLINE", "area": "62", "number": "33121234"}],
    "emails": [{"ownership": "COMPANY", "address": "contato@empresa.com", "domain": "empresa.com"}],
    "mainActivity": {"id": 6201500, "text": "Desenvolvimento de programas de computador sob encomenda"},
    "sideActivities": [{"id": 6202300, "text": "Consultoria em tecnologia da informação"}],
    "registrations": [
        {
            "number": "123456789",
            "state": "GO",
            "enabled": True,
            "statusDate": "2010-06-01",
            "status": {"id": 1, "text": "Habilitado"},
            "type": {"id": 1, "text": "IE Normal"},
        }
    ],
    "suframa": [],
    "company": {
        "id": 987654,
        "name": "Empresa Fantasia Comercio LTDA",
        "equity": 500000,
        "nature": {"id": 2062, "text": "Sociedade Empresária Limitada"},
        "size": {"id": 5, "acronym": "DEMAIS", "text": "Demais"},
        "simples": {"optant": True, "since": "2010-06-01"},
        "simei": {"optant": False, "since": None},
        "members": [
            {
                "since": "2010-05-25",
                "person": {
                    "id": "abc",
                    "type": "NATURAL",
                    "name": "Fulano de Tal",
                    "taxId": "***123456**",
                },
                "role": {"id": 49, "text": "Sócio-Administrador"},
            }
        ],
    },
}


def test_mapear_resposta_cnpja():
    dados = _mapear_resposta(AMOSTRA_CNPJA)

    assert dados["razao_social"] == "Empresa Fantasia Comercio LTDA"
    assert dados["nome_fantasia"] == "Empresa Fantasia"
    assert dados["cnpj"] == "11222333000181"
    assert dados["municipio"] == "Itapaci"
    assert dados["uf"] == "GO"
    assert dados["cnae_principal"] == "Desenvolvimento de programas de computador sob encomenda"
    assert dados["situacao_cadastral"] == "Ativa"
    assert dados["porte"] == "Demais"
    assert dados["capital_social"] == 500000
    assert dados["opcao_simples"] is True
    assert dados["data_opcao_simples"] == "2010-06-01"
    assert dados["opcao_mei"] is False
    assert dados["telefone_rfb"] == "(62) 33121234"
    assert dados["email_rfb"] == "contato@empresa.com"

    assert dados["cnaes_secundarios"] == [
        {"codigo": "6202300", "descricao": "Consultoria em tecnologia da informação"}
    ]
    assert dados["socios"] == [
        {"nome": "Fulano de Tal", "qualificacao": "Sócio-Administrador", "cpf_parcial": "***123456**"}
    ]
    assert dados["inscricoes_estaduais"] == [
        {"uf": "GO", "numero": "123456789", "situacao": "Habilitado"}
    ]


def test_consultar_cnpj_rejeita_documento_invalido():
    with pytest.raises(CnpjConsultaError):
        consultar_cnpj("123")


def test_consultar_cnpj_aceita_cnpj_alfanumerico(monkeypatch):
    """CNPJ alfanumérico (Lei/IN RFB 2.229/2024): 12 primeiras posições podem ter letras."""
    import app.services.cnpj_service as servico

    capturado = {}

    class RespostaFalsa:
        status_code = 200

        def json(self):
            return AMOSTRA_CNPJA

    def get_falso(url, timeout):
        capturado["url"] = url
        return RespostaFalsa()

    monkeypatch.setattr(servico.requests, "get", get_falso)
    dados = servico.consultar_cnpj("12ABC34501DE35")
    assert "12ABC34501DE35" in capturado["url"]
    assert dados["razao_social"]


def test_consultar_cnpj_trata_erro_http(monkeypatch):
    import app.services.cnpj_service as servico

    class RespostaFalsa:
        status_code = 429

        def json(self):
            return {}

    monkeypatch.setattr(servico.requests, "get", lambda url, timeout: RespostaFalsa())
    with pytest.raises(CnpjConsultaError, match="Limite"):
        servico.consultar_cnpj("11222333000181")
