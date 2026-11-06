# Proposta progressiva — relatório comparativo F2

**Data:** 06/11/2026, America/Sao_Paulo. **Projeto:** QTRE. **Estado:** proposta; nenhuma implementação deste relatório foi iniciada. **Checkout inspecionado:** branch `codex/quant-research-environment`, HEAD `e1d5f56`, com alterações locais preexistentes. Este documento não altera o protocolo de pesquisa nem a lógica financeira.

**Estado da publicação:** antes de concluir esta proposta, `origin/main` avançou até `ec90d2c` e passou a conter a implementação de sensibilidade a custos, seus artefatos e o resumo descritivo. A Tarefa 1 deve confirmar novamente esse estado antes de usar os exemplos.

## Objetivo e hipótese de trabalho

Tornar a avaliação sintética F2 mais rápida de executar, ler e revisar por meio de uma saída única para momentum, `equal_weight` e `cash` nos três cenários de custos já registrados. A hipótese operacional é que consolidar artefatos auditados e suas restrições de comparabilidade reduz trabalho manual e risco de interpretação sem exigir uma nova estratégia, parâmetro ou cálculo contábil.

**Baseline:** nove execuções persistidas em [`examples/f2_cost_sensitivity_v1`](../examples/f2_cost_sensitivity_v1), o `sensitivity.json`, as auditorias individuais e os resumos por execução. A comparação hoje exige consultar essas saídas separadamente. O relatório proposto deve ser derivado delas, sem executar novamente o motor na etapa de leitura.

## Evidência verificada neste checkout

- [`run_cost_sensitivity`](../src/qtre/validation/cost_sensitivity.py) já produz as nove execuções, faz replay e auditoria, concilia caixa e NAV e compara pares de custos. Quando fills ou agenda de NAV diferem, informa `NOT_COMPARABLE_EXECUTION_CHANGED`.
- [`summarize_f1_run`](../src/qtre/validation/summary.py) já resume uma execução após replay e omite retorno acumulado se alguma marca estiver incompleta.
- A [sensibilidade F2](sensibilidade-custos-f2-v1.md) registra que as quantidades de fills mudam entre custos para momentum e `equal_weight`; os NAVs finais observados nesses cenários não formam um teste válido de monotonicidade. Uma marca `NAV_INCOMPLETO` impede retorno acumulado para essas séries. `cash` tem NAV completo na fixture.
- O [protocolo F2](protocolo-pesquisa-f2-v1.md) fixa estratégias, custos e limites de interpretação. A fixture possui quatro decisões sintéticas, sem janela fora da amostra ou evidência de desempenho B3.

### Medição exploratória de execução

Com `PYTHONPATH=src python3 examples/benchmark_f1.py --repetitions 5`, a mediana observada foi **50,06 ms** para o motor e **67,71 ms** para o replay, com `economic_hash` `7436b10b3141ac69869d0fcf14c38f9e3e722561855123f1cca86a6d27cdbb54`. O benchmark usa **três ciclos**, enquanto os artefatos F2 acima usam quatro decisões. Uma execução de `cProfile` apontou trabalho relevante em parsing de snapshot, serialização e processamento de ações, mas a instrumentação aumenta muito os tempos absolutos. Não há medição antes/depois nem evidência de gargalo em escala real. Por isso, otimizar o motor não é a primeira entrega desta proposta.

## Primeira entrega recomendada

Criar um **leitor de comparação F2** que receba um diretório com os nove subdiretórios persistidos e gere:

1. Um JSON consolidado, com versão de esquema, identidade das execuções e seus caminhos de origem.
2. Uma tabela legível por pessoa com estratégia, cenário, decisões, sessões, ordens, fills, custos por rubrica, caixa, NAV final e estado do retorno.
3. Um quadro de comparabilidade entre cenários, preservando o resultado de `compare_pair` e sua justificativa. A presença de NAV final em duas execuções não autoriza concluir monotonicidade quando a execução mudou.
4. Um aviso explícito para `NAV_INCOMPLETO`, ausência de nocional em `cash`, divergência de configuração ou falha de replay/auditoria. Métricas indisponíveis devem permanecer `null` com motivo, sem imputação.

**Entradas:** diretório de artefatos F2 já persistidos, manifestos, tabelas e auditorias. **Saídas:** relatório JSON e apresentação textual ou Markdown determinística. **Unidades:** BRL para caixa/NAV/custos; bps para custos relativos quando houver nocional; contagens inteiras para decisões, sessões, ordens e fills. **Regra temporal:** o leitor não decide nem negocia; aceita apenas resultados cujo replay e auditoria causal tenham passado. Os timestamps e identidades continuam nos manifestos de origem.

### Critérios de aceite da primeira entrega

- Os números do relatório coincidem exatamente com os artefatos persistidos, sem arredondamento adicional que altere a contabilidade.
- Uma execução adulterada ou auditada como inválida bloqueia a comparação e identifica o subdiretório afetado.
- Retorno acumulado permanece indisponível se houver qualquer `NAV_INCOMPLETO`; o relatório não exibe zero como substituto.
- A monotonicidade só aparece como teste quando agenda e quantidades de fills são idênticas. Nos demais casos, aparece `NOT_COMPARABLE_EXECUTION_CHANGED`.
- A saída é determinística para o mesmo conjunto de arquivos e não modifica as execuções de origem.

## Sequência de trabalho

| Etapa | Trabalho | Evidência de conclusão |
|---|---|---|
| 1. Contrato | Definir campos, estados e exemplo de saída a partir das nove execuções existentes | Esquema pequeno, unidades e casos indisponíveis documentados |
| 2. Leitor | Implementar agregação somente leitura, reutilizando replay, auditoria e comparação existentes | Relatório reproduzível para a fixture F2 |
| 3. Validação | Testar saída esperada, adulteração, NAV incompleto, fills diferentes e rerun determinístico | Testes relevantes e `make check` com resultados registrados |
| 4. Uso | Documentar um comando e um exemplo curto de interpretação | Um pesquisador consegue gerar e ler o relatório sem abrir nove diretórios |

Depois dessa entrega, medir o fluxo com um conjunto maior e representativo. Somente um gargalo reproduzido deve motivar otimização de parsing, ações ou serialização, preservando o hash econômico e as invariantes contábeis. Dados B3 auditados, walk-forward e ML seguem as dependências do [roadmap](roadmap-competencias.md); este relatório não os antecipa.

## Prompts para as primeiras tarefas

Execute na ordem. Cada tarefa deve reler o estado atual do checkout; o HEAD e os arquivos locais citados acima podem mudar.

### Tarefa 1 — fechar o contrato, sem código

> No repositório QTRE, leia `AGENTS.md`, `docs/especificacao-tecnica.md`, `docs/roadmap-competencias.md`, `docs/protocolo-pesquisa-f2-v1.md`, `docs/sensibilidade-custos-f2-v1.md` e `docs/proposta-relatorio-comparativo-f2-2026-11-06.md`. Confira branch, status e os artefatos F2 existentes. Produza um contrato v1 para o relatório comparativo F2 em `docs/`, com esquema JSON mínimo, campos e unidades, estados de indisponibilidade, regras de identidade/comparabilidade e um exemplo derivado dos artefatos persistidos verificados. Diferencie valores observados de campos propostos. Não altere motor, estratégias, parâmetros, contabilidade ou artefatos de execução. Preserve alterações locais. Ao concluir, apresente arquivos modificados, decisões de contrato, limites e verificação documental; não faça commit nem push.

### Tarefa 2 — implementar o leitor sobre o contrato aprovado

> Implemente o leitor de comparação F2 definido no contrato v1 produzido na tarefa anterior. Receba o diretório das nove execuções persistidas, reutilize `replay_f1`, `audit_f1_run` e `compare_pair`, e gere JSON determinístico mais uma tabela legível. Leia os artefatos sem modificá-los. Bloqueie execuções inválidas ou adulteradas; mantenha `null` e motivo para retorno com `NAV_INCOMPLETO` e para custos em bps sem nocional; preserve `NOT_COMPARABLE_EXECUTION_CHANGED` quando fills ou agenda diferirem. Use `Decimal` para valores monetários. Não mude lógica financeira nem os parâmetros do protocolo. Respeite arquivos locais não versionados e não faça commit nem push. Adicione testes focados nos critérios de aceite e execute `make check`; informe os comandos e resultados observados, o diff e limitações.

### Tarefa 3 — revisar e tornar reproduzível

> Revise independentemente a implementação do relatório comparativo F2 contra o contrato v1 e os artefatos persistidos. Verifique identidade/configuração, reconciliação, causalidade delegada à auditoria, ausência de imputação de `NAV_INCOMPLETO`, comparabilidade condicional, determinismo e se a leitura modifica algum arquivo de origem. Corrija apenas falhas dentro desse escopo. Acrescente à documentação um comando de execução e um exemplo curto de interpretação que não sugira desempenho B3. Execute os testes pertinentes e `make check`, registre resultados reais e reporte riscos residuais. Preserve alterações paralelas; não faça commit nem push.

## Validação e limites deste documento

**Comandos executados para esta análise:** `git status --short --branch`, `git rev-parse --short HEAD`, leituras dos contratos/código, `PYTHONPATH=src python3 examples/benchmark_f1.py --repetitions 5` e `PYTHONPATH=src python3 -m cProfile -s cumulative examples/benchmark_f1.py --repetitions 1`. A suíte de testes não foi executada para esta proposta documental. Não há implementação, resultado novo de estratégia ou conclusão de investimento. O benchmark pequeno e a carga local não demonstram escalabilidade ou latência de mercado.
