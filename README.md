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

**Concluído (AXDP-003 — todos os 10 itens da seção 8 do handoff):**
- Login com sessão e perfis de usuário (admin/operador); primeiro acesso
  cria o administrador sem precisar de CLI/env var
- Banco de dados fora da pasta do sistema (configurável via
  `AXIOM_DP_DATA_DIR`), modo **WAL**
- Servidor de rede local acessado por navegador (sem mais
  `pywebview`/janela única)
- Provedor de CNPJ trocado para a **CNPJá** — sócios/QSA, CNAEs
  secundários, inscrições estaduais, porte, capital social, opção
  Simples/MEI, situação especial; suporte a CNPJ alfanumérico e aos
  campos CAEPF/CEI/CNO
- Máscaras completas nos formulários (CPF, CNPJ/CPF dinâmico, CEI, CNO,
  CAEPF, IE por UF, telefone, CEP, valores monetários)
- `titulo_pt`: corrige capitalização de dados vindos em CAIXA ALTA da
  RFB/planilhas, só na exibição e na geração de documentos (o dado bruto
  nunca é alterado no banco)
- Importação das 537 empresas e 1.798 rubricas do escritório
  (idempotente — `scripts/importar_dados_escritorio.py`)
- Motor de cálculo de contracheque/pró-labore avulso: INSS progressivo,
  IRRF por tabela + redutor 2026 (Lei 15.270/2025), FGTS — **ver os
  avisos de "valores a confirmar" no topo de
  `app/services/calculo_folha.py` e `scripts/seed_tabelas_fiscais.py`
  antes de usar para fechar folha real**
- Telas de emissão do recibo avulso (empresa/empregado ou pró-labore sem
  registro, itens por rubrica, cálculo automático, `.docx` em 2 vias) e
  CRUD de frases de quitação parametrizáveis por empresa
- Módulo de relatórios (`/relatorios`): histórico de documentos emitidos
  e recibos avulsos, filtrável por período, empresa e tipo

**Avisos importantes antes de uso em produção real (não são bugs — são
pontos que dependem de confirmação humana, documentados também no código):**
1. O mapeamento de campos da CNPJá (`app/services/cnpj_service.py`) foi
   feito pela documentação pública da API — o ambiente de desenvolvimento
   não teve saída de rede para validar contra uma chamada real.
2. As tabelas de INSS/IRRF semeadas são as de 02/2024 — a mais recente
   que os dados de treinamento confirmam com confiança. Confira se ainda
   são as vigentes antes de fechar uma folha real; se não forem,
   adicione uma tabela nova (nunca sobrescreva a antiga).
3. Os códigos de incidência de cada `Rubrica` (vindos da planilha
   `RELAÇÃO_DE_RUBRICA.xls`) não tinham documentação de significado —
   o motor de cálculo assume "0 = não incide, qualquer outro código =
   incide". Confirme essa convenção com o Charles.

**Antes de continuar o desenvolvimento, leia [`HANDOFF_CLAUDE_CODE.md`](./HANDOFF_CLAUDE_CODE.md).**
Ele consolida todas as decisões de arquitetura e o roteiro detalhado
das próximas sprints — é o documento mais atualizado do repositório.

## Estrutura

```
app/
├── models/          Empresa (+CNAE/Sócio/IE secundários), Empregado, Usuario,
│                    TemplateDocumento, DocumentoEmitido, Rubrica, TabelaINSS,
│                    TabelaIRRF, TabelaIRRFRedutor, FraseQuitacao, ReciboAvulso
├── routes/          rotas server-side (CRUD, emissão, recibos, relatórios) e API JSON
├── services/        CNPJá, motor de geração de documentos, cálculo de folha, recibo avulso
├── utils/           titulo_pt (capitalização pt-BR de dados em CAIXA ALTA)
├── docs_templates/  48 modelos .docx prontos para merge (docxtpl)
├── templates/       telas HTML (Jinja2)
└── static/          CSS, JS (IMask vendorizado), imagens (arte da tela de login)
scripts/             seed de templates/tabelas fiscais/frase e importação de planilhas
tests/               suíte pytest (77 testes) — CRUD, auth, cálculo de folha, geração de
                     documentos/recibos, importação, tudo via requisição HTTP real
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
python scripts/importar_dados_escritorio.py   # importa as 537 empresas e as 1.798 rubricas do escritório
python scripts/seed_tabelas_fiscais.py        # tabelas INSS/IRRF + redutor 2026 (CONFIRA os valores antes de uso real)
python scripts/seed_frase_quitacao.py         # frase de quitação "Tradicional"
python main.py
```

`importar_dados_escritorio.py` é idempotente — pode ser rodado de novo
(por exemplo, se o Charles enviar uma planilha atualizada) sem duplicar
registros; empresas casam pelo documento (CNPJ/CPF) e rubricas pelo
código.

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
