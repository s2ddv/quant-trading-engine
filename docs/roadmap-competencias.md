# QTRE: plano de pesquisa e competências

## Tese do projeto

Construir uma plataforma reproduzível para investigar estratégias em ações brasileiras. O estudo inicial pergunta se momentum cross-sectional 12–2, em uma carteira long-only, supera um benchmark investível **após custos**, fora da amostra. O resultado pode ser negativo: a entrega é a qualidade da pesquisa e da engenharia, não uma promessa de lucro.

A conversa “Análise de projetos Quant” originou a direção de portfólio: reunir pesquisa quantitativa, backtesting rigoroso, validação estatística e integração com o projeto Monte Carlo GBM. Este documento transforma essa direção em entregas verificáveis. A [especificação técnica](especificacao-tecnica.md) permanece como contrato detalhado do motor.

## Objetivos e metas

**Objetivo principal:** publicar um estudo reproduzível que permita a outra pessoa verificar, passo a passo, uma conclusão sobre momentum 12–2 em ações brasileiras. Uma conclusão de ausência de vantagem também satisfaz o objetivo se o método for sólido.

| Horizonte | Meta | Critério de conclusão |
|---|---|---|
| Agora | Preservar e consolidar a F0 local | Contratos e fixtures documentados, testes verdes e estado Git compreendido antes de versionar |
| Próxima entrega | Fazer o primeiro corte vertical sintético da F1 | Cinco ou mais instrumentos, 13+ meses, sinal manualmente verificável, ordens só após decisão e caixa/NAV conciliados |
| Depois | Tornar o backtest auditável | Replay determinístico, manifesto, teste de vazamento, custos e eventos corporativos demonstrados em fixtures adversas |
| Pesquisa | Avaliar robustez em vez de maximizar uma métrica | Protocolo pré-definido, baselines, separação temporal, todas as tentativas registradas e sensibilidade a custos |
| Integração | Reusar Monte Carlo como laboratório de risco | Adaptador opcional, parâmetros e seed registrados, cenários comparados com risco histórico |
| Publicação | Produzir um caso de portfólio defensável | Fonte de dados e direitos auditados, relatório líquido fora da amostra, limites explícitos e instruções de reprodução |

## Forma de trabalho

1. **Uma pergunta e uma entrega por etapa.** Antes do código, registrar entrada, saída, invariantes e um exemplo esperado. Dividir a F1 em dados/universo, sinal, carteira, execução e livro; integrar apenas depois de verificar cada contrato.
2. **Inspecionar antes de alterar.** Conferir branch, alterações locais, especificação e interfaces dos projetos relacionados. Preservar trabalho não versionado e evitar mudanças em repositórios vizinhos sem necessidade explícita.
3. **Testar causalidade e contabilidade primeiro.** Fixtures pequenas com resposta calculada à mão; testes adversos para dado futuro, suspensão, preço ausente, split e dividendo. Testes estatísticos entram depois que o motor econômico estiver correto.
4. **Guardar evidência de cada execução.** Registrar versão do código, hash do snapshot, configuração, seed, calendário, custos e resultado. Relatar separadamente teste sintético, replay e qualquer avaliação com dados reais.
5. **Revisar cada marco.** Conferir diff, rodar testes relevantes, comparar a saída com o aceite e atualizar documentação de limitações. Só então avançar para a fase seguinte. Não alterar parâmetros após consultar o teste final sem registrar uma nova hipótese.

**Fora do escopo imediato:** corretora e ordens reais, previsão por ML, múltiplas estratégias e afirmações de desempenho B3. Essas ideias só entram se acrescentarem evidência à pergunta de pesquisa depois do primeiro backtest auditável.

## Competência → evidência pública

| Competência | O que construir | Evidência de conclusão |
|---|---|---|
| Quant Developer | Dados versionados, interfaces entre módulos, motor determinístico, contabilidade e replay | Testes de contratos, manifesto com hashes, execução offline reproduzível e conciliação de caixa/NAV |
| Quant Researcher | Hipótese registrada antes do teste, sinal 12–2, baselines e comparação fora da amostra | Protocolo de pesquisa congelado, períodos separados, métricas líquidas, análise de sensibilidade e relatório de limites |
| Quant Trader | Regras de elegibilidade, formação de ordens, latência, lotes, liquidez e custos | Livro de ordens/fills auditável, limites respeitados e sensibilidade a custos e capacidade |
| Estatística aplicada | Incerteza, múltiplas tentativas, estabilidade temporal e regimes | Intervalos ou bandas com método declarado, número de hipóteses testadas, resultados por subperíodo e controles negativos |
| Integração de modelos | Cenários de risco com o `quant-simulation-framework` | Adaptador versionado, entrada/saída reproduzível e comparação entre cenários simulados e risco histórico sem chamar simulação de previsão validada |

## Sequência de entregas

1. **F0 — base causal consolidada e versionada.** Parser e fixtures sintéticas preservados, com contratos de disponibilidade temporal, identidade de instrumentos e calendário testados. Esta etapa não é um backtest.
2. **F1 — backtest vertical sintético.** Criar uma fixture com pelo menos 13 meses e 5 instrumentos; implementar universo datado, 12–2, carteira, execução na sessão seguinte, custos, ações corporativas, livro e NAV. Entrega: caso manual conciliado e trilha de cada decisão.
3. **F2 — validação de pesquisa.** Pré-definir hipótese, parâmetros, benchmark e protocolo de seleção; separar desenvolvimento, validação e teste final. Acrescentar walk-forward quando houver histórico suficiente, controles negativos, testes de vazamento, sensibilidade a custos e relatório de todas as tentativas. Entrega: replay e auditoria causal reproduzíveis. Fixtures sintéticas demonstram o método, não desempenho B3.
4. **F3 — integração Monte Carlo.** Consumir o `quant-simulation-framework` por adaptador opcional e versão fixada. Usar histórico de retornos e pesos do QTRE para cenários de perda, drawdown e concentração; comparar com risco realizado fora da amostra. Manter separadas as hipóteses GBM, os cenários Student-t e as métricas históricas. Entrega: cenário reproduzível com seed, parâmetros, origem dos dados e limitações.
5. **F4 — dados brasileiros auditados.** Só introduzir barras, eventos, universo histórico e benchmark reais após verificar licença, cobertura, deslistados, correções e timestamps de disponibilidade. Entrega: relatório de qualidade de dados e rótulos explícitos para qualquer viés remanescente.
6. **F5 — estudo final congelado.** Fixar código, dados, parâmetros e janela de teste antes de avaliá-la; publicar comparação líquida, incerteza, turnover, exposição, capacidade aproximada e falhas. Entrega: comando único de reprodução, manifesto e relatório que distingue achado, hipótese e limitação.

## Regras de pesquisa

- Nenhuma decisão usa um dado com `available_at` posterior ao instante da decisão. Ordens geradas após o fechamento não recebem fill nesse fechamento.
- O mesmo snapshot, configuração, versão de código e seed produzem o mesmo resultado; mudanças entram em novo manifesto.
- Benchmark, custos, calendário, universo e tratamento de dividendos são definidos antes de comparar estratégias. Métricas brutas e líquidas aparecem lado a lado.
- Cada tentativa de estratégia ou ajuste de parâmetro fica registrada. O período de teste final não serve para escolher parâmetros; se for consultado para isso, deixa de ser teste final.
- Incerteza estatística usa método adequado à dependência temporal e ao tamanho da amostra. Não usar um p-valor isolado como prova de vantagem econômica.
- Dados sintéticos testam software e causalidade. Resultados de ações B3 exigem fonte, direitos e auditoria próprios.

## Próxima entrega concreta

A F1 atual demonstra uma formação mensal em fixture de 14 meses e cinco instrumentos, com sinal, ordens, fills e NAV conciliado. A revisão de 04/11 corrigiu erros de custos, ações corporativas e causalidade; seus casos de regressão são parte da suíte. Ainda faltam vendas e rebalanceamentos sucessivos, serialização das saídas e replay independente para concluir o motor previsto na especificação. A sondagem yfinance foi antecipada a pedido do usuário e continua exploratória, sem alimentar o backtest causal.

Próxima entrega: persistir os artefatos e reconstruir o livro por replay, acrescentando vendas e repetição de rebalanceamentos com casos manuais. Nenhum resultado sintético ou de cobertura da API demonstra desempenho de ações B3. A numeração desta sequência organiza competências; para os critérios técnicos de aceite F0–F4, prevalece a tabela da especificação técnica.
