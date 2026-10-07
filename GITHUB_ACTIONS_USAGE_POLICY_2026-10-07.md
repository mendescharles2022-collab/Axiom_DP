# AVISO GLOBAL — USO RESPONSÁVEL DO GITHUB ACTIONS

**Data:** 07/10/2026  
**Autoridade:** Proprietário — Charles Mendes  
**Aplicação:** obrigatória neste repositório e para qualquer agente, IA, automação ou colaborador que atue nele.

## Motivo

A conta GitHub atingiu aproximadamente **90% da franquia disponível de GitHub Actions**. A auditoria global identificou consumo acelerado provocado por grande volume de execuções, inclusive rajadas de workflows disparadas a cada push, múltiplos workflows para o mesmo commit e repetição de gates/falhas durante ciclos de desenvolvimento.

GitHub Actions é um recurso limitado e **não deve ser usado como ambiente rotineiro de tentativa, depuração ou repetição de testes que possam ser executados localmente**.

## Ordem obrigatória

1. **Priorizar testes locais.** Durante implementação, correção, refatoração e investigação, executar localmente todos os testes, lint, compilação, regressões e validações que não dependam estritamente da infraestrutura do GitHub.
2. **Não disparar Actions a cada pequeno commit/checkpoint.** Commits intermediários não justificam, por si só, CI remoto completo.
3. **Evitar duplicidade.** Um mesmo push não deve acionar vários workflows equivalentes ou regressões redundantes.
4. **Falha repetitiva não deve virar loop.** Se um workflow falhar por causa já identificada, corrigir e validar localmente antes de novo disparo remoto.
5. **Regressões completas no GitHub devem ser excepcionais.** Reservá-las para checkpoints relevantes, fechamento de fase, validação final, integração importante ou quando o ambiente remoto for tecnicamente indispensável.
6. **Preferir acionamento manual (`workflow_dispatch`)** para workflows caros, regressões completas, empacotamentos, auditorias e tarefas ocasionais, salvo quando houver justificativa objetiva para execução automática.
7. **Artefatos devem ser mínimos.** Não publicar logs, pacotes, bancos, relatórios ou blobs grandes/repetitivos sem necessidade; aplicar retenção curta quando apropriado.
8. **Projetos congelados não devem consumir Actions por desenvolvimento.** O congelamento vigente permanece integralmente válido. Este aviso de governança **não autoriza retomada** de nenhum projeto.
9. **Hórus Gestão:** por ser o sistema atualmente autorizado a evoluir, pode usar CI quando necessário, mas deve obedecer à mesma disciplina: testes locais durante construção e Actions apenas nos gates remotos realmente necessários.
10. Antes de criar ou alterar qualquer workflow, avaliar explicitamente o impacto sobre a franquia mensal.

## Regra operacional

> **LOCAL PRIMEIRO. ACTIONS SOMENTE QUANDO AGREGAR VALIDAÇÃO REMOTA REAL.**

A existência de GitHub Actions não substitui testes locais e não autoriza consumo automático ilimitado.

Qualquer agente que trabalhe neste repositório deve ler e respeitar este aviso antes de criar, reativar, ampliar ou executar workflows.

---
**Esta política é de governança e preservação de recursos. Não altera escopo funcional, não descongela projetos e não autoriza desenvolvimento fora das ordens vigentes do proprietário.**
