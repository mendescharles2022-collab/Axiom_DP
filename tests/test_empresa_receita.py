from app.extensions import db


def _dados_cnpja_fake():
    return {
        "razao_social": "Empresa Atualizada LTDA",
        "nome_fantasia": "Fantasia Nova",
        "cnpj": "11222333000181",
        "logradouro": "Rua Nova",
        "numero": "10",
        "municipio": "Itapaci",
        "uf": "GO",
        "cnae_principal": "Comércio varejista",
        "situacao_cadastral": "Ativa",
        "porte": "Demais",
        "capital_social": 10000,
        "opcao_simples": True,
        "data_opcao_simples": "2020-01-01",
        "opcao_mei": False,
        "cnaes_secundarios": [{"codigo": "1234567", "descricao": "Atividade secundária"}],
        "socios": [{"nome": "Ciclano", "qualificacao": "Sócio", "cpf_parcial": "***111222**"}],
        "inscricoes_estaduais": [{"uf": "GO", "numero": "987654321", "situacao": "Habilitado"}],
    }


def test_atualizar_receita_preenche_empresa_e_relacionados(app, auth_client, monkeypatch):
    from app.models.empresa import Empresa

    with app.app_context():
        empresa = Empresa(razao_social="Empresa Antiga", cnpj="11222333000181", tipo_inscricao="CNPJ")
        db.session.add(empresa)
        db.session.commit()
        empresa_id = empresa.id

    import app.routes.paginas as paginas

    monkeypatch.setattr(paginas, "consultar_cnpj", lambda cnpj: _dados_cnpja_fake())

    resp = auth_client.post(f"/empresas/{empresa_id}/atualizar-receita", follow_redirects=True)
    assert resp.status_code == 200
    assert "atualizados" in resp.get_data(as_text=True)

    with app.app_context():
        empresa = Empresa.query.get(empresa_id)
        assert empresa.nome_fantasia == "Fantasia Nova"
        assert empresa.porte == "Demais"
        assert float(empresa.capital_social) == 10000
        assert len(empresa.cnaes_secundarios) == 1
        assert empresa.cnaes_secundarios[0].codigo == "1234567"
        assert len(empresa.socios) == 1
        assert empresa.socios[0].nome == "Ciclano"
        assert len(empresa.inscricoes_estaduais) == 1
        assert empresa.inscricoes_estaduais[0].numero == "987654321"


def test_atualizar_receita_bloqueado_para_cpf(app, auth_client):
    from app.models.empresa import Empresa

    with app.app_context():
        empresa = Empresa(razao_social="Produtor Rural", cnpj="123.456.789-00", tipo_inscricao="CPF")
        db.session.add(empresa)
        db.session.commit()
        empresa_id = empresa.id

    resp = auth_client.post(f"/empresas/{empresa_id}/atualizar-receita", follow_redirects=True)
    assert resp.status_code == 200
    assert "só está disponível para empresas com CNPJ" in resp.get_data(as_text=True)
