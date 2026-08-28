# Axiom_DP — Handoff para Claude Code

## Leia isto primeiro

**Não recomece do zero.** Este projeto já tem uma fundação real, testada e
funcionando (sprints AXDP-000, AXDP-001 e AXDP-002). Este documento existe
para consolidar tudo o que foi decidido nas conversas anteriores com o
Klaus (Claude no chat) e servir de roteiro para as próximas sprints
(AXDP-003 em diante). Trabalhe **em cima** da estrutura existente.

O responsável por escopo e decisões de arquitetura deste projeto é o
Klaus — este documento reflete decisões já tomadas por ele com o Charles
(dono do projeto, contador, escritório de contabilidade em Itapaci/GO).
Ao encontrar uma decisão de arquitetura não coberta aqui, seguir o
espírito das decisões já tomadas (pragmatismo, escritório pequeno,
sem dependências desnecessárias) em vez de introduzir complexidade nova.

---

## 1. O que já existe e funciona (não reescrever)

```
Axiom_DP/
├── app/
│   ├── __init__.py            # app factory Flask
│   ├── config.py              # paths (DB, templates, output)
│   ├── extensions.py          # instância db (SQLAlchemy)
│   ├── models/
│   │   ├── empresa.py         # Empresa
│   │   ├── empregado.py       # Empregado
│   │   ├── documento.py       # TemplateDocumento (catálogo)
│   │   └── emissao.py         # DocumentoEmitido (histórico)
│   ├── routes/
│   │   ├── paginas.py         # TODAS as rotas server-side (CRUD + emissão)
│   │   ├── empresas.py        # API JSON (CRUD + busca CNPJ)
│   │   └── empregados.py      # API JSON (CRUD)
│   ├── services/
│   │   ├── cnpj_service.py    # consulta CNPJ (hoje: BrasilAPI — TROCAR por CNPJá, ver seção 4)
│   │   └── document_engine.py # motor de geração via docxtpl
│   ├── docs_templates/        # 48 modelos .docx já convertidos p/ docxtpl (Jinja)
│   │                          # + catalogo.json + um .campos.json por modelo
│   ├── templates/             # HTML (Jinja2) das telas
│   └── static/{css,js,img}/   # inclui app/static/img/login-ilustracao.svg (pronta)
├── database/                  # SQLite (axiom_dp.sqlite3) — ver seção 2 sobre mover pra fora
├── scripts/
│   ├── converter_templates_docxtpl.py   # conversor [colchete] -> {{ jinja }} (já rodado)
│   └── seed_templates.py                # popula templates_documentos a partir do catalogo.json
├── main.py                    # hoje sobe Flask + pywebview — SUBSTITUIR (ver seção 3)
├── requirements.txt
└── docs/ARQUITETURA.md        # roadmap original (parcialmente superado por este doc)
```

**Testado e funcionando** (não é esqueleto vazio):
- CRUD completo de Empresa e Empregado, com validações e mensagens flash
- Busca de CNPJ integrada ao formulário (hoje via BrasilAPI)
- Os 48 modelos de documento (avisos, contratos, declarações, advertências,
  cartas, recibos) convertidos para Jinja/docxtpl, com campos extras
  mapeados em `.campos.json` por modelo
- Tela de emissão: escolher empresa → empregado → modelo → preencher
  campos extras → gerar `.docx` → baixar
- Histórico de documentos emitidos por empresa
- Suite de teste rodada via `test_client()` do Flask: os 48 modelos geram
  documento com sucesso via requisição HTTP real

**Bugs já corrigidos durante o desenvolvimento (não reintroduzir)**:
- Jinja não chama métodos Python automaticamente — por isso
  `document_engine.py` constrói um contexto com `SimpleNamespace` e
  valores já resolvidos (ex.: `empresa.endereco_completo()` é chamado
  ANTES de entrar no contexto, nunca `{{ empresa.endereco_completo }}`
  esperando chamada automática)
- Identificadores Jinja não podem começar com dígito (ex.: `13o_salario`
  quebra; usar `campo_13o_salario`)
- Cabeçalho e rodapé do Word ficam em partes separadas do XML
  (`section.header`, `section.footer`) — sempre incluir ao iterar
  parágrafos para converter placeholders
- `None` nunca deve chegar cru a um `{{ }}` (vira a string `"None"` no
  documento) — sempre tratar com valor default `""`

---

## 2. Banco de dados

**Decisão: continuar com SQLite** (banco pequeno, não justifica Postgres).
Ativar **modo WAL** (`PRAGMA journal_mode=WAL`) para suportar múltiplos
usuários da rede local lendo/escrevendo sem travar.

**Mover o arquivo do banco para FORA da pasta do sistema** — o Charles
foi explícito sobre isso: atualizações do programa não podem arriscar o
banco. Usar um caminho configurável (variável de ambiente
`AXIOM_DP_DATA_DIR`, com fallback sensato tipo
`%APPDATA%/Axiom_DP/` no Windows) em vez do hoje hardcoded
`database/axiom_dp.sqlite3` dentro da própria pasta do projeto.

---

## 3. Arquitetura de acesso: servidor local de rede (não mais pywebview)

Decisão tomada com o Charles: **não é mais um app desktop isolado por
máquina**. É um **servidor Flask rodando em uma máquina do escritório**,
acessado **via navegador** pelas outras estações da rede local (não é
nuvem — permanece dentro da rede do escritório).

Isso significa:
- **Remover `pywebview`** de `main.py` — o servidor sobe com
  `app.run(host="0.0.0.0", port=...)` e todo mundo acessa via navegador,
  inclusive a própria máquina que hospeda.
- Adicionar **autenticação de sessão web** (Flask-Login ou equivalente)
  com tela de login própria.
- **Perfis de usuário / permissões**: pelo menos um perfil admin
  (cadastro de usuários, tudo liberado) e um perfil operador (uso do
  dia a dia: emitir documentos, ver clientes, sem gerenciar usuários).
  Modelar como `Usuario` (login, hash de senha, perfil, ativo) — usar
  `werkzeug.security` para hash (já é dependência do Flask, não precisa
  adicionar lib nova).
- **Tela de login com imagem**: já existe em
  `app/static/img/login-ilustracao.svg` (abstrata, tons navy/dourado/teal,
  aprovada pelo Charles). Usar como arte lateral/hero da tela de login.

---

## 4. Consulta de CNPJ: trocar BrasilAPI → CNPJá

Decisão tomada após avaliar as opções: a **CNPJá** é mais completa e
resolve mais necessidades do que a BrasilAPI usada até aqui.

- Endpoint público (sem necessidade de cadastro/chave):
  `https://open.cnpja.com/office/{cnpj}` (cnpj só dígitos, sem máscara)
- Limite gratuito: **5 requisições/minuto por IP** — suficiente para uso
  interativo de escritório (não é consulta em lote)
- Retorna, além do básico: **CNAE principal e TODOS os secundários**
  (com descrição), **quadro societário (QSA)** completo, **inscrições
  estaduais por UF** (número + situação — cobre boa parte da necessidade
  de Sintegra sem precisar de link manual), SUFRAMA, opção pelo
  Simples/MEI com datas, situação especial (recuperação judicial,
  falência), capital social, porte, telefone e e-mail
- Defasagem de dados: até 45 dias (não é D+0, mas é aceitável para
  cadastro)

**Ação**: reescrever `app/services/cnpj_service.py` mantendo a mesma
assinatura pública (`consultar_cnpj(cnpj) -> dict`, `CnpjConsultaError`)
para não quebrar as rotas que já a consomem — só troca o provedor por
dentro e enriquece o dicionário de retorno com os campos novos (ver
seção 5 para onde esses campos vão no modelo).

Links de Sintegra como **fallback manual** (caso a CNPJá não tenha a IE
de algum estado específico):
- Nacional: `https://www.sintegra.gov.br`
- Goiás (oficial, Sefaz-GO): `http://appasp.sefaz.go.gov.br/Sintegra/Consulta/default.asp`

---

## 5. Expansão do modelo de dados

### 5.1 `Empresa` — campos novos

- `tipo_inscricao`: enum/string `CNPJ` | `CPF` (necessário: a lista de
  537 clientes do Charles tem 491 CNPJ + 46 CPF — produtor rural,
  autônomo, empregador doméstico)
- `caepf`, `cei`, `cno`: strings, opcionais — inscrições alternativas
  quando não há CNPJ (ver seção 6 para formato/máscara de cada uma)
- `nome_fantasia`, `data_fundacao`, `porte`, `capital_social`,
  `situacao_especial`, `data_situacao_especial`, `telefone_rfb`,
  `email_rfb`, `opcao_simples`, `data_opcao_simples`, `opcao_mei`,
  `data_opcao_mei` — todos vindos da CNPJá
- `status` (Ativo/Inativo) e `forma_envio` — vêm da planilha de clientes
  do Charles (ver seção 7), útil manter mesmo não vindo da RFB

### 5.2 Novas tabelas relacionadas a `Empresa`

- **`CnaeSecundario`**: `empresa_id` (FK), `codigo`, `descricao` —
  um-para-muitos, pois uma empresa pode ter vários CNAEs secundários
- **`Socio`** (quadro societário/QSA): `empresa_id` (FK), `nome`,
  `qualificacao`, `cpf_parcial` (a API só devolve CPF mascarado do sócio)
- **`InscricaoEstadual`**: `empresa_id` (FK), `uf`, `numero`,
  `situacao` — uma empresa pode ter IE em mais de um estado

### 5.3 Correção de capitalização (dados vindos em CAIXA ALTA da RFB)

Criar utilitário `titulo_pt(texto: str) -> str`:
- Guarda o dado bruto como veio da RFB no banco (auditoria/fidelidade)
- Aplica Title Case só na **exibição** e na **geração de documentos**
- Regras: conectores em minúsculo (`de`, `da`, `do`, `dos`, `das`, `e`);
  siglas/formas societárias sempre maiúsculas (`LTDA`, `ME`, `EPP`,
  `EIRELI`, `S/A`, `MEI`, `EI`)
- Aplicar em: razão social, nome fantasia, nome de sócio, endereço,
  nome de empregado

### 5.4 Usuário e autenticação

- **`Usuario`**: `nome`, `login` (único), `senha_hash`, `perfil`
  (`admin` | `operador`), `ativo`, `criado_em`, `ultimo_acesso`

### 5.5 Motor de folha de pagamento (contracheque/pró-labore avulso)

- **`TabelaINSS`**: histórica por vigência —
  `vigencia_inicio`, `vigencia_fim` (nullable = vigente), `faixas_json`
  (lista de `{ate, aliquota}`), `teto_contribuicao`
- **`TabelaIRRF`**: histórica por vigência —
  `vigencia_inicio`, `vigencia_fim`, `faixas_json` (lista de
  `{ate, aliquota, parcela_deduzir}`), `deducao_por_dependente`
- **`TabelaIRRFRedutor`**: a partir de 01/2026 (Lei nº 15.270/2025) —
  regra adicional aplicada DEPOIS do cálculo pela tabela progressiva
  tradicional: zera o imposto até R$ 5.000,00/mês; reduz parcialmente
  entre R$ 5.000,01 e R$ 7.350,00 (fórmula:
  `redutor = 978,62 - (0,133145 × rendimento_tributavel)`, limitado ao
  valor do imposto apurado); sem redução acima de R$ 7.350,00. **Não é
  substituição da tabela antiga — é uma etapa extra.** Modelar de forma
  que o cálculo de qualquer competência passada continue correto (por
  isso as tabelas são históricas por vigência, nunca hardcoded fixas)
- **`Rubrica`** (catálogo global, não por empresa): `codigo`, `nome`,
  `tipo` (`P`=provento, `D`=desconto, `I`=informativo),
  `incidencia_irrf`, `incidencia_inss`, `incidencia_fgts`,
  `incidencia_pis` — importar da planilha `RELAÇÃO_DE_RUBRICA.xls`
  fornecida pelo Charles (1.798 registros, ver seção 7)
- **`ReciboAvulso`** (contracheque ou pró-labore avulso):
  `empresa_id`, `empregado_id` (nullable — pró-labore pode ser de sócio
  sem registro de empregado), `competencia`, `tipo`
  (`contracheque`|`pro_labore`), `frase_quitacao_id` (FK, ver 5.6),
  `criado_em`
- **`ReciboAvulsoItem`**: `recibo_id` (FK), `rubrica_id` (FK),
  `referencia`, `valor_provento`, `valor_desconto`

### 5.6 Modelos de recibo e frase de quitação parametrizável

- **`FraseQuitacao`**: `nome` (ex.: "Tradicional", "Cliente X —
  obrigatória"), `texto`. Pelo menos duas ao nascer: a tradicional
  ("Declaro que recebi o valor descrito e dou plena quitação do que me
  é devido até o momento.") e a que o Charles vai enviar depois (com a
  frase exigida por um cliente específico dele)
- Cada `ReciboAvulso` referencia qual frase usar; permitir definir uma
  frase padrão por empresa para não precisar escolher toda emissão
- Usar o arquivo `Recibo_de_Salário_-_Sebastião_das_Dores_da_Silva.xls`
  (já fornecido pelo Charles) como referência estrutural para os
  modelos: cabeçalho do empregador (nome, endereço, CEI/CAEPF/CNO),
  dados do empregado (código, nome, CBO, função), tabela de rubricas
  usadas (código, descrição, referência, proventos, descontos), totais
  (vencimentos, descontos, líquido), bases de cálculo (salário-base,
  base INSS, base FGTS, FGTS do mês, base IRRF, faixa IRRF), área de
  assinatura e data. O Charles vai mandar ainda um modelo específico
  com uma frase de assinatura obrigatória — quando chegar, tratar como
  mais uma opção de `FraseQuitacao` + eventual variação de layout, não
  substituir o modelo padrão.

---

## 6. Biblioteca de máscaras — cobertura completa exigida

O Charles foi explícito: **nenhum campo de identificação deve ficar sem
máscara**. Usar uma lib de mask no frontend (ex.: IMask.js) aplicada a
todos os formulários (`empresa_form.html`, `empregado_form.html`, e os
novos de usuário/recibo). Formatos confirmados:

| Campo | Máscara | Observação |
|---|---|---|
| CPF | `000.000.000-00` | |
| CNPJ | `AA.AAA.AAA/AAAA-00` | **Alfanumérico desde 31/07/2026** (Lei/IN RFB 2.229/2024): 12 primeiras posições aceitam A-Z **e** 0-9; os 2 dígitos verificadores finais continuam sempre numéricos. CNPJs antigos (só números) continuam válidos e coexistem. Regex de validação NÃO pode ser `^\d{14}$` — precisa aceitar letras maiúsculas nas 12 primeiras posições. |
| CEI | `00.000.00000/00` | 12 dígitos |
| CNO | `00.000.00000/00` | mesma composição do CEI (substituiu CEI de obras) |
| CAEPF | `00.000.000/0000-00` | 14 dígitos (9 do CPF + 3 sequencial + 2 verificadores) |
| CNAE | `0000-0/00` | principal e todos os secundários |
| Inscrição Estadual (GO) | `00.000.000-0` | 9 dígitos; **outros estados têm formatos diferentes** — não hardcodar um único formato genérico, tratar por UF ou aceitar formato livre com validação leve fora de GO |
| Telefone | `(00) 0000-0000` / `(00) 00000-0000` | fixo/celular |
| CEP | `00000-000` | |
| Datas | `00/00/0000` | |
| Valores monetários | `R$ 0.000,00` | |

---

## 7. Dados fornecidos pelo Charles — prontos para importar

Arquivos já recebidos e analisados (devem estar anexados ou re-enviados
pelo Charles ao Code):

1. **`Relação_de_Empresas_-.xlsx`** — 537 clientes: 491 com CNPJ, 46
   com CPF. Colunas: Razão Social, Tipo de Inscrição, Inscrição, Status
   (Ativo/Inativo), Forma de Envio. Importar direto para `Empresa`
   (campos básicos), deixando os campos que só a CNPJá preenche (CNAE,
   sócios, etc.) vazios até o usuário clicar em "atualizar dados da
   Receita" empresa por empresa (não fazer 537 chamadas automáticas de
   uma vez — respeitar o limite de 5 req/min da CNPJá).
2. **`RELAÇÃO_DE_RUBRICA.xls`** — 1.798 rubricas (Código, Nome, Tipo,
   Incidência IRRF/INSS/FGTS/PIS). Importar direto para `Rubrica` como
   catálogo global (parece ser a tabela padrão de um sistema de folha
   conhecido — os códigos e nomes são genéricos, não específicos de uma
   empresa).
3. **`Recibo_de_Salário_-_Sebastião_das_Dores_da_Silva.xls`** —
   referência estrutural de layout (ver seção 5.6).
4. **`Recibo_Comercial_Neres_-_Priscila_Garcia_Matos.doc`** — já foi
   usado para criar o modelo "Recibo de Pagamento de Verbas" (já está
   entre os 48 templates convertidos, não precisa reprocessar).

Quando o Charles enviar o modelo de recibo com a frase de assinatura
obrigatória de um cliente específico, seguir a orientação da seção 5.6.

---

## 8. Ordem sugerida de execução

1. Mover banco para pasta externa configurável + ativar WAL
2. `Usuario` + login/logout + decorators de permissão + tela de login
   (usar a imagem já pronta em `app/static/img/login-ilustracao.svg`)
3. Remover `pywebview` de `main.py`; servir via `host="0.0.0.0"`
4. Trocar `cnpj_service.py` para CNPJá; expandir `Empresa` + tabelas
   novas (CNAEs secundários, sócios, inscrições estaduais)
5. Máscaras em todos os formulários (tabela da seção 6)
6. Utilitário `titulo_pt` aplicado em exibição e geração de documento
7. Importar as 537 empresas e as 1.798 rubricas
8. Tabelas históricas de INSS/IRRF + redutor 2026 + `Rubrica` já
   populada → motor de cálculo de contracheque/pró-labore avulso
9. Modelos de recibo (parametrização de frase de quitação)
10. Módulo de relatórios/histórico (em cima do `DocumentoEmitido` e do
    novo `ReciboAvulso`)

Cada item deve ser entregue testado (o padrão até aqui foi sempre gerar
teste via `test_client()` do Flask antes de considerar concluído — não
quebrar esse hábito).
