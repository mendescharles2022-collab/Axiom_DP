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

**Em andamento (AXDP-003 em diante):** login com perfis de usuário,
migração para servidor de rede local (acesso por navegador em vez de
janela única), troca do provedor de CNPJ para a CNPJá (mais completo:
sócios, CNAEs secundários, inscrições estaduais), suporte a CNPJ
alfanumérico e a CAEPF/CEI/CNO, biblioteca de máscaras completa, e um
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
database/            banco SQLite (deve ser movido para fora da pasta do sistema — ver handoff)
```

## Como rodar (estado atual do código)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python scripts/seed_templates.py    # popula o catálogo de modelos (1x, ou de novo ao adicionar modelos)
python main.py
```

Isso abre uma janela do programa (via `pywebview`) conectada ao Flask
local e ao SQLite, criado automaticamente em `database/axiom_dp.sqlite3`
na primeira execução. **Este modo de execução está sendo substituído**
por um servidor de rede com login — ver seção 3 do handoff.

## Notas técnicas importantes

- A consulta de CNPJ hoje usa a **BrasilAPI**; a próxima sprint troca
  para a **CNPJá** (mais completa — ver handoff, seção 4). A troca é
  isolada em `app/services/cnpj_service.py`.
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
