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
  IRRF por tabela + redutor 2026 (Lei 15.270/2025), FGTS, salário-família
  (automático para contracheque de empregado elegível, a partir de
  `Empregado.numero_dependentes_salario_familia`) — **ver os avisos de
  "valores a confirmar" no topo de `app/services/calculo_folha.py` e
  `scripts/seed_tabelas_fiscais.py` antes de usar para fechar folha real**
- Telas de emissão do recibo avulso (empresa/empregado ou pró-labore sem
  registro, itens por rubrica, cálculo automático, `.docx` em 2 vias) e
  CRUD de frases de quitação parametrizáveis por empresa
- Módulo de relatórios (`/relatorios`): histórico de documentos emitidos
  e recibos avulsos, filtrável por período, empresa e tipo

**Atualizado com dados oficiais fornecidos pelo Charles:**
- `scripts/seed_tabelas_fiscais.py` agora semeia o histórico completo de
  INSS (2012 a 2026, 15 vigências) e IRRF (2015 a 2026, 5 vigências),
  a partir de um dataset oficial — não são mais estimativas.
- O redutor de 2026 (Lei 15.270/2025) foi corrigido: é uma fórmula única
  e contínua em toda a faixa 0–R$ 7.350 (não "zera tudo até R$ 5.000,
  reduz parcial depois" como a primeira versão implementava — havia uma
  faixa estreita, ~R$ 4.620 a R$ 5.000, em que essa leitura simplificada
  cobrava menos imposto do que devido). Ver `app/models/tabela_irrf_redutor.py`.
- A incidência de IRRF de cada `Rubrica` agora usa o lookup real da
  Tabela 21 do eSocial (`INCIDENCIAS_IRRF_QUE_NAO_ENTRAM_NA_BASE` em
  `app/services/calculo_folha.py`), não mais a heurística "0 = não
  incide, resto incide" — vários códigos de isenção (diárias, ajuda de
  custo, indenização, abono pecuniário de férias etc.) são != 0 mas não
  entram na base tributável.
- Adicionado salário-família (`TabelaSalarioFamilia`, histórico 1999-2026):
  soma automaticamente no contracheque de empregado elegível
  (remuneração dentro do limite + dependentes cadastrados), sem entrar
  na base de INSS/IRRF/FGTS. Novos campos em Empregado:
  `numero_dependentes_irrf` (dedução do IRRF) e
  `numero_dependentes_salario_familia` (elegibilidade ao benefício) —
  são contagens separadas porque as regras de dependente são diferentes
  para cada um. Pró-labore de sócio não recebe o benefício.

**Concluído (ADENDO A — múltiplos modelos visuais de recibo):**
- Catálogo `TemplateRecibo` (tipo, nome, arquivo, ativo) com 4 modelos
  prontos, no mesmo padrão visual dos 48 documentos de DP (navy/dourado,
  Cambria para títulos, Calibri para dados):
  - Contracheque — Clássico (2 vias empregador/empregado) e Moderno
  - Pró-labore — Clássico (2 vias) e Moderno
- Na tela de novo recibo avulso, o campo "Modelo visual do recibo" lista
  só os modelos do tipo escolhido (contracheque × pró-labore), filtrado
  via JS conforme o campo "Tipo" muda; se nada for escolhido, usa o
  primeiro modelo ativo cadastrado para aquele tipo.
- `app/services/recibo_engine.py` foi reescrito de geração manual
  (python-docx) para `docxtpl`, igual ao motor dos 48 documentos —
  renderiza o `.docx` do modelo escolhido (`ReciboAvulso.template_recibo_id`)
  com o contexto do cálculo (itens, INSS, IRRF, FGTS, salário-família).
- `scripts/gerar_templates_recibo.py`: script de autoria (python-docx) que
  gera os 4 `.docx` em `app/docs_templates_recibo/` — só precisa rodar de
  novo se os modelos visuais forem alterados.
- `scripts/seed_templates_recibo.py`: popula o catálogo `TemplateRecibo`
  (idempotente por arquivo).
- Corrigido também: `Empresa.endereco_completo()` não deixa mais "CEP"
  solto sem valor quando a empresa ainda não tem endereço preenchido
  (comum nas importadas antes de "Atualizar dados da Receita").

**Concluído (ADENDO B — modo manutenção com porta dedicada):**
- `ConfiguracaoManutencao` (registro único): `ativo`, `titulo`, `mensagem`,
  `previsao_retorno`, `atualizado_por`/`atualizado_em`.
- Porta principal (`main.py`, `AXIOM_DP_PORT`, padrão **5600** — antes
  5151): antes de qualquer rota (exceto login/logout/estáticos), checa
  se o modo manutenção está ligado; se estiver, mostra uma página de
  aviso (título + mensagem + previsão de retorno) para todo mundo que
  não estiver logado como administrador. Um admin já logado continua
  usando o sistema normalmente mesmo com a manutenção ligada.
- Porta de administração (`manutencao.py`, `AXIOM_DP_PORT_MANUTENCAO`,
  padrão **5601**): app Flask mínimo, separado, só acessível com login
  de administrador — única função é ligar/desligar o modo manutenção e
  editar título/mensagem/previsão de retorno. Compartilha o mesmo banco
  SQLite (modo WAL) da porta principal, mas não depende de mais nada
  dela — por isso continua no ar mesmo que a porta principal caia ou
  seja reiniciada no meio de uma atualização.
- `python main.py` sobe as duas com um único comando: a porta principal
  roda em primeiro plano e, se a de manutenção ainda não estiver no ar,
  sobe ela como processo do sistema operacional **desacoplado** (não um
  processo filho) — testado de verdade: matar o processo da porta
  principal (`kill -9`) não derruba a de manutenção, e reiniciar a
  principal detecta que a de manutenção já está rodando e não duplica.
  Para subir só a de manutenção isoladamente, `python manutencao.py`.

**Avisos que ainda dependem de confirmação humana antes de uso em
produção real (documentados também no código):**
1. O mapeamento de campos da CNPJá (`app/services/cnpj_service.py`) foi
   feito pela documentação pública da API — o ambiente de desenvolvimento
   não teve saída de rede para validar contra uma chamada real.
2. A dedução por dependente do IRRF (R$ 189,59) foi mantida constante em
   todas as vigências semeadas — não veio no dataset oficial fornecido;
   é um valor que não muda há vários reajustes, mas vale confirmar.
3. Os códigos de incidência de INSS/FGTS/PIS de cada `Rubrica` (vindos
   da planilha `RELAÇÃO_DE_RUBRICA.xls`) ainda usam a heurística "0 = não
   incide, qualquer outro código = incide" — falta o Charles enviar a
   tabela oficial de incidências de INSS/FGTS/PIS do eSocial (equivalente
   à Tabela 21 que já resolveu o IRRF) para trocar pela mesma lógica de
   lookup.

**Antes de continuar o desenvolvimento, leia [`HANDOFF_CLAUDE_CODE.md`](./HANDOFF_CLAUDE_CODE.md).**
Ele consolida todas as decisões de arquitetura e o roteiro detalhado
das próximas sprints — é o documento mais atualizado do repositório.

## Estrutura

```
app/
├── models/          Empresa (+CNAE/Sócio/IE secundários), Empregado, Usuario,
│                    TemplateDocumento, DocumentoEmitido, Rubrica, TabelaINSS,
│                    TabelaIRRF, TabelaIRRFRedutor, TabelaSalarioFamilia,
│                    FraseQuitacao, TemplateRecibo, ReciboAvulso,
│                    ConfiguracaoManutencao
├── routes/          rotas server-side (CRUD, emissão, recibos, relatórios) e API JSON
├── services/        CNPJá, motor de geração de documentos, cálculo de folha, recibo avulso
├── utils/           titulo_pt (capitalização pt-BR de dados em CAIXA ALTA)
├── docs_templates/  48 modelos .docx prontos para merge (docxtpl)
├── docs_templates_recibo/  4 modelos visuais de recibo (contracheque/pró-labore ×
│                    clássico/moderno), gerados por scripts/gerar_templates_recibo.py
├── templates/       telas HTML (Jinja2)
└── static/          CSS, JS (IMask vendorizado), imagens (arte da tela de login)
scripts/             seed de templates/tabelas fiscais/frase e importação de planilhas
tests/               suíte pytest (99 testes) — CRUD, auth, cálculo de folha, geração de
                     documentos/recibos, importação, modo manutenção, tudo via
                     requisição HTTP real
dados_para_importar/ planilhas fornecidas pelo escritório (clientes, rubricas, recibo de referência)
database/            banco SQLite (fica fora da pasta do sistema — ver "Dados e variável de ambiente")
main.py              porta principal (5600) + sobe a porta de manutenção se preciso
manutencao.py        porta de administração/manutenção (5601), processo independente
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
python scripts/seed_tabelas_fiscais.py        # histórico INSS 2012-2026, IRRF 2015-2026 + redutor 2026
python scripts/seed_frase_quitacao.py         # frase de quitação "Tradicional"
python scripts/seed_templates_recibo.py       # catálogo dos 4 modelos visuais de recibo
python main.py
```

`importar_dados_escritorio.py` é idempotente — pode ser rodado de novo
(por exemplo, se o Charles enviar uma planilha atualizada) sem duplicar
registros; empresas casam pelo documento (CNPJ/CPF) e rubricas pelo
código.

`python main.py` sobe **duas portas** com o mesmo comando:
- **Principal** (`0.0.0.0:5600`, configurável via `AXIOM_DP_PORT`): o
  sistema completo — é nela que o escritório trabalha no dia a dia,
  em `http://localhost:5600` ou pelo IP da máquina na rede local. No
  primeiro acesso, a tela pede para criar a conta de administrador;
  depois disso, login é sempre exigido.
- **Manutenção** (`0.0.0.0:5601`, configurável via
  `AXIOM_DP_PORT_MANUTENCAO`): painel de administrador para ligar/
  desligar uma mensagem de aviso na porta principal durante uma
  atualização. Só acessível com login de administrador (o mesmo criado
  na porta principal). Sobe como processo independente — reiniciar ou
  derrubar a porta principal não tira ela do ar.

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
- `manutencao.py` é uma segunda app Flask independente que reaproveita
  o mesmo objeto `db` (Flask-SQLAlchemy suporta `db.init_app()` em mais
  de uma app), mas usa seu **próprio** `LoginManager` — o de
  `app.extensions` não pode ser compartilhado entre as duas apps porque
  `login_view`/`user_loader` ficam no próprio objeto, não por app.

## Empacotamento (sprint futura)

Quando as telas principais estiverem prontas, empacotar com PyInstaller
em modo pasta, gerando um executável + pasta de dependências, copiável
para outra máquina sem precisar instalar Python. Detalhes a definir
junto com a migração para servidor de rede (handoff, seção 3).
