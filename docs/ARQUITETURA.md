# Axiom_DP — Arquitetura e Roadmap

Projeto independente do ecossistema Axiom. Programa local (não-web),
com banco próprio, para automatizar a emissão dos documentos de
Departamento Pessoal (avisos, contratos, declarações, advertências,
recibos etc.) a partir de um cadastro de empresas e empregados.

## Stack

| Camada             | Tecnologia                                   |
|--------------------|-----------------------------------------------|
| Linguagem          | Python 3.11+                                   |
| Backend            | Flask (app factory, roda localmente em 127.0.0.1) |
| ORM / Banco        | SQLAlchemy + SQLite (arquivo único, `database/axiom_dp.sqlite3`) |
| Geração de docs    | docxtpl (Jinja2 dentro do próprio .docx — sem manipular XML na mão) |
| Interface          | pywebview (janela nativa do SO, sem "cara de navegador") |
| Empacotamento      | PyInstaller (modo pasta: .exe + pasta + banco) |
| Consulta de CNPJ   | BrasilAPI (gratuita, sem chave) como padrão; adaptador plugável para trocar de provedor depois |

## Decisão de arquitetura

**Banco único, multi-empresa.** Uma tabela `empresas`, com `empregados`,
`documentos_emitidos` etc. referenciando `empresa_id` por FK. Permite
relatórios cruzados entre clientes do escritório e backup único.

## Modelo de dados (visão inicial)

- **Empresa**: razão social, nome fantasia, CNPJ, endereço, CNAE,
  situação cadastral, dados obtidos via API (cache local) + campos manuais.
- **Empregado**: vínculo com `empresa_id`, dados pessoais, dados
  funcionais (cargo, setor, admissão, salário, jornada), dados bancários.
- **TemplateDocumento**: catálogo dos modelos (categoria, nome, arquivo
  .docx, lista de variáveis esperadas).
- **DocumentoEmitido**: histórico (empresa, empregado, template usado,
  data de emissão, caminho do arquivo gerado, usuário/observação).

## Motor de geração de documentos

Os 47+ modelos do pacote de DP serão migrados de placeholders
`[NOME COMPLETO]` para variáveis Jinja `{{ empregado.nome }}` dentro do
próprio .docx, usando **docxtpl**. Isso elimina a necessidade de
manipular XML: o merge vira `doc.render(contexto)`.

## Roadmap de Sprints

- **AXDP-000 — Fundação** *(esta entrega)*: estrutura de pastas, app
  factory Flask, configuração, modelos base (Empresa, Empregado),
  banco SQLite inicial, `main.py` com pywebview, tela local mínima
  (lista de empresas) só pra provar que a base funciona ponta a ponta.
- **AXDP-001 — Cadastro de Empresas**: CRUD completo + botão de busca
  de CNPJ (BrasilAPI) preenchendo os campos automaticamente.
- **AXDP-002 — Cadastro de Empregados**: CRUD vinculado à empresa,
  formulário com os campos usados pelos templates.
- **AXDP-003 — Motor de Documentos**: importação dos 47 modelos do
  pacote de DP, conversão para docxtpl, tela de emissão (escolher
  empresa + empregado + modelo → gerar .docx pronto).
- **AXDP-004 — Histórico e Consulta SEFAZ (opcional)**: log de emissões,
  avaliação de integração com serviço pago consolidado de SEFAZ/IE.
- **AXDP-005 — Empacotamento**: PyInstaller, ícone, instalador simples,
  teste em máquina limpa.

Cada sprint é entregue como código real e funcional, não esqueleto vazio.
