# Axiom_DP

Sistema de Departamento Pessoal do escritório: cadastro de empresas e
empregados, emissão automatizada de documentos (avisos, contratos,
declarações, advertências, recibos), com dados extraídos direto da
Receita Federal.

## Status atual

**Concluído e testado (AXDP-000 a AXDP-002):**
- Cadastro completo de Empresas e Empregados (CRUD, busca de CNPJ)
- 48 modelos de documentos de DP convertidos para geração automática
  (docxtpl/Jinja), com verificação de que nenhum campo fica sem mapear
- Motor de geração: escolhe empresa + empregado + modelo → preenche os
  campos específicos → gera o `.docx` pronto → fica no histórico
- Testado ponta a ponta via requisição HTTP real, não só em memória

**Concluído (AXDP-003):** login com sessão e perfis de usuário
(admin/operador), banco de dados fora da pasta do sistema com WAL,
migração para servidor de rede local acessado por navegador (sem mais
`pywebview`/janela única), e troca do provedor de CNPJ para a **CNPJá**
(sócios/QSA, CNAEs secundários, inscrições estaduais, porte, capital
social, opção Simples/MEI, situação especial), com suporte a CNPJ
alfanumérico e aos campos CAEPF/CEI/CNO para clientes sem CNPJ.

**Em andamento:** biblioteca de máscaras completa nos formulários, e um
motor de emissão de contracheque/pró-labore avulso com tabelas
históricas de INSS e IRRF.

**Antes de continuar o desenvolvimento, leia [`HANDOFF_CLAUDE_CODE.md`](./HANDOFF_CLAUDE_CODE.md).**
Ele consolida todas as decisões de arquitetura e o roteiro detalhado
das próximas sprints — é o documento mais atualizado do repositório.

## Estrutura

```
app/
├── models/          Empresa, Empregado, TemplateDocumento, DocumentoEmitido
├── routes/          rotas server-side (CRUD + emissão) e API JSON
├── services/        consulta de CNPJ e motor de geração de documentos
├── docs_templates/  48 modelos .docx prontos para merge (docxtpl)
├── templates/       telas HTML (Jinja2)
└── static/          CSS, JS, imagens (inclui a arte da tela de login)
scripts/             conversão de templates e seed do catálogo
dados_para_importar/ planilhas fornecidas pelo escritório (clientes, rubricas, recibo de referência)
database/            banco SQLite (fica fora da pasta do sistema — ver "Dados e variável de ambiente")
```

## Dados e variável de ambiente

O banco SQLite e os documentos gerados ficam **fora** da pasta de
instalação, para que atualizações do programa não arrisquem os dados:

- Windows: `%APPDATA%\Axiom_DP\`
- Linux/Mac (dev): `~/.axiom_dp/`

Para usar outro caminho (ex.: pasta compartilhada da rede), defina a
variável de ambiente `AXIOM_DP_DATA_DIR` antes de rodar o programa. O
banco roda em modo **WAL**, para suportar múltiplas estações lendo e
gravando ao mesmo tempo sem travar.

A chave de assinatura de sessão (login) é gerada automaticamente e
guardada em `secret_key` dentro dessa mesma pasta de dados na primeira
execução. Em produção, prefira definir `AXIOM_DP_SECRET_KEY` explicitamente.

## Como rodar (estado atual do código)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python scripts/seed_templates.py    # popula o catálogo de modelos (1x, ou de novo ao adicionar modelos)
python main.py
```

Isso sobe o servidor Flask em `0.0.0.0:5151` (porta configurável via
`AXIOM_DP_PORT`), acessível pelo navegador de qualquer estação da rede
local do escritório — inclusive a própria máquina que hospeda, em
`http://localhost:5151`. No primeiro acesso, a tela pede para criar a
conta de administrador; depois disso, login é sempre exigido.

## Notas técnicas importantes

- A consulta de CNPJ usa a **CNPJá** (`open.cnpja.com`, endpoint público,
  5 requisições/minuto por IP — ver handoff, seção 4), isolada em
  `app/services/cnpj_service.py`. O mapeamento de campos foi feito a
  partir da documentação pública da API (o ambiente de desenvolvimento
  não teve saída de rede para validar contra uma chamada real) — confira
  o aviso no topo do arquivo antes de depender dele em produção.
- Na tela de uma empresa já cadastrada (com CNPJ), o botão "Atualizar
  dados da Receita" busca os dados atuais e substitui CNAEs secundários,
  sócios e inscrições estaduais pelos mais recentes.
- Jinja não chama métodos Python automaticamente: o motor de documentos
  sempre resolve valores (como `empresa.endereco_completo()`) antes de
  montar o contexto — nunca depender de chamada implícita no template.
- Identificadores Jinja não podem começar com dígito.
- Cabeçalho/rodapé do Word ficam em partes separadas do XML — sempre
  incluir ao processar placeholders de um `.docx`.

## Empacotamento (sprint futura)

Quando as telas principais estiverem prontas, empacotar com PyInstaller
em modo pasta, gerando um executável + pasta de dependências, copiável
para outra máquina sem precisar instalar Python. Detalhes a definir
junto com a migração para servidor de rede (handoff, seção 3).
