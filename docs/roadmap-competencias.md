# QTRE: plano de pesquisa e competências

## Tese do projeto

Construir uma plataforma reproduzível para investigar estratégias em ações brasileiras. O estudo inicial pergunta se momentum cross-sectional 12–2, em uma carteira long-only, supera um benchmark investível **após custos**, fora da amostra. Depois, uma extensão com aprendizado de máquina (ML) testará se um ranking supervisionado acrescenta valor ao momentum sob o mesmo universo, execução e custos. O resultado de qualquer comparação pode ser negativo: a entrega é a qualidade da pesquisa e da engenharia, não uma promessa de lucro.

A direção do portfólio reúne pesquisa quantitativa, backtesting rigoroso e validação estatística neste motor Python. Este documento transforma essa direção em entregas verificáveis. A [especificação técnica](especificacao-tecnica.md) permanece como contrato detalhado do motor.

## Objetivos e metas

**Objetivo principal:** publicar um estudo reproduzível que permita a outra pessoa verificar, passo a passo, a estratégia momentum 12–2 em ações brasileiras e se uma extensão supervisionada de ML melhora seus resultados líquidos fora da amostra. O momentum permanece como referência; ausência de vantagem em qualquer etapa também satisfaz o objetivo se o método for sólido.

| Horizonte | Meta | Critério de conclusão |
|---|---|---|
| Concluído | Consolidar a F0 e demonstrar uma formação sintética da F1 | Contratos versionados; fixture de 14 meses e cinco instrumentos; sinal manual, execução posterior, custos e NAV testados |
| Concluído | Persistir a execução e reconstruir o livro por replay independente | Esquema 1, manifesto e hashes; replay offline reproduz caixa, posições, recebíveis e NAV; adulteração é detectada nos testes |
| Concluído | Demonstrar uma venda e o segundo rebalanceamento sintético | Alvos baseados no patrimônio disponível, venda antes de compra, caixa e base de custo conciliados em valores manuais, ordens causais |
| Concluído no sintético | Generalizar ciclos mensais de carteira | Terceira e quarta decisões, lotes, custos, eventos corporativos, deslistagem declarada ou incompleta e replay compatível |
| Concluído no sintético — F2 | Controles e sensibilidade a custos | Protocolo v1, auditoria causal, `cash`, `equal_weight` e nove cenários de custo com replay e testes; monotonicidade só é exigida com fills fixos |
| Depois — F2 | Avaliar robustez quando houver histórico suficiente | Separação temporal, tentativas registradas e incerteza com método declarado |
| Depois dos dados auditados | Validar o momentum como referência em janelas de desenvolvimento e validação | Universo, benchmark e custos comparáveis; tentativas registradas; janela final reservada para comparação com ML |
| Depois da referência | Avaliar um ranking supervisionado de ML | Fatores e rótulos causais; modelo simples antes de modelos complexos; mesma carteira e execução; avaliação temporal e registro do modelo |
| Publicação | Comparar referência e ML na janela final reservada | Retorno líquido, risco, giro, custos, incerteza e limites; fonte de dados e direitos auditados; reprodução de ambas as execuções |

## Forma de trabalho

1. **Uma pergunta e uma entrega por etapa.** Antes do código, registrar entrada, saída, invariantes e um exemplo esperado. Dividir a F1 em dados/universo, sinal, carteira, execução e livro; integrar apenas depois de verificar cada contrato.
2. **Inspecionar antes de alterar.** Conferir branch, alterações locais, especificação e interfaces dos projetos relacionados. Preservar trabalho não versionado e evitar mudanças em repositórios vizinhos sem necessidade explícita.
3. **Testar causalidade e contabilidade primeiro.** Fixtures pequenas com resposta calculada à mão; testes adversos para dado futuro, suspensão, preço ausente, split e dividendo. Testes estatísticos entram depois que o motor econômico estiver correto.
4. **Guardar evidência de cada execução.** Registrar versão do código, hash do snapshot, configuração, seed, calendário, custos e resultado. Relatar separadamente teste sintético, replay e qualquer avaliação com dados reais.
5. **Revisar e versionar cada marco.** Conferir diff, rodar testes relevantes, comparar a saída com o aceite e atualizar documentação de limitações. Fazer commits periódicos e coesos usando a skill `commit`, após conferir exatamente o que será incluído; informar os hashes e manter push separado. Só então avançar para a fase seguinte. Não alterar parâmetros após consultar o teste final sem registrar uma nova hipótese.

**Fora do escopo imediato:** corretora e ordens reais, treino de ML, aprendizado por reforço (RL), múltiplas estratégias e afirmações de desempenho B3. O experimento supervisionado de ML está planejado após dados auditados e uma referência comparável; RL só será considerado se houver uma pergunta sequencial específica, histórico suficiente e avaliação separada.

## Competência → evidência pública

| Competência | O que construir | Evidência de conclusão |
|---|---|---|
| Quant Developer | Dados versionados, interfaces entre módulos, motor determinístico, contabilidade e replay | Testes de contratos, manifesto com hashes, execução offline reproduzível e conciliação de caixa/NAV |
| Quant Researcher | Hipótese registrada antes do teste, sinal 12–2, baselines e comparação fora da amostra | Protocolo de pesquisa congelado, períodos separados, métricas líquidas, análise de sensibilidade e relatório de limites |
| Quant Trader | Regras de elegibilidade, formação de ordens, latência, lotes, liquidez e custos | Livro de ordens/fills auditável, limites respeitados e sensibilidade a custos e capacidade |
| Estatística aplicada | Incerteza, múltiplas tentativas, estabilidade temporal e regimes | Intervalos ou bandas com método declarado, número de hipóteses testadas, resultados por subperíodo e controles negativos |
| ML aplicado à pesquisa | Ranking supervisionado dos ativos elegíveis, mantendo o momentum como referência | Fatores disponíveis na decisão, rótulos futuros bem definidos, modelo e tentativas versionados, comparação líquida fora da amostra no mesmo motor |

## Sequência de entregas

1. **F0 — base causal consolidada e versionada.** Parser e fixtures sintéticas preservados, com contratos de disponibilidade temporal, identidade de instrumentos e calendário testados. Esta etapa não é um backtest.
2. **F1 — backtest vertical sintético (concluído no escopo).** A fixture controlada demonstra universo datado, sinal 12–2, quatro decisões mensais, compra, venda total e parcial, custos, lotes, split, dividendo, deslistagem com valor declarado ou desconhecido, livro e NAV. Artefatos dos esquemas 1 a 5 permitem replay independente. O valor desconhecido conserva a posição e torna o NAV incompleto; a próxima decisão exige uma marca completa. A liquidação e os preços são hipóteses sintéticas, sem resultado B3.
3. **F2 — validação sintética (controles implementados).** Protocolo, auditoria causal, controles `cash` e `equal_weight`, sensibilidade a custos e replay estão versionados. O resumo descritivo F2 foi revisado nesta entrega local. Walk-forward e inferência estatística ainda exigem histórico suficiente. Fixtures sintéticas demonstram o método, não desempenho B3.
4. **F3 — dados brasileiros limitados.** Só introduzir barras, eventos, universo histórico e benchmark reais após verificar licença, cobertura, deslistados, correções e timestamps de disponibilidade. Entrega: relatório de qualidade de dados e rótulos explícitos para qualquer viés remanescente.
5. **F4 — referência histórica auditável.** Definir o corte de desenvolvimento, validação e teste final antes da análise; avaliar o momentum e os controles somente nas janelas de desenvolvimento e validação. Registrar tentativas, custos, benchmark e limites sem usar a janela final para escolher parâmetros. Entrega: referência reproduzível pronta para a comparação.
6. **Extensão futura — ranking supervisionado de ML.** Formular antes do treino a pergunta incremental: um ranking aprendido entre ativos elegíveis melhora a carteira de momentum? Construir fatores apenas com dados disponíveis em cada decisão, definir rótulo pelo retorno futuro do horizonte escolhido, separar treino e validação no tempo e impedir que rótulos atravessem os cortes. Começar por um modelo linear regularizado; testar árvores somente se houver amostra e justificativa. Registrar fatores, rótulos, versões, hiperparâmetros, seed, tentativas e previsões. Usar o mesmo universo, regras de carteira, execução e custos da referência. Selecionar o modelo apenas na validação; acurácia ou probabilidade de alta, isoladas, não demonstram valor econômico. Entrega: experimento reproduzível com métricas preditivas e resultado líquido na validação.
7. **Comparação futura congelada.** Fixar código, dados, parâmetros e modelos antes de abrir uma única janela final reservada para momentum, controles e ML. Publicar comparação líquida, incerteza, giro, exposição, capacidade aproximada e falhas; se o ML não melhorar a referência de modo robusto, relatar esse resultado. Entrega: comando de reprodução, manifestos e relatório que distingue achado, hipótese e limitação. RL pode ser proposto depois, em estudo separado, se uma decisão sequencial concreta justificar sua complexidade.

## Regras de pesquisa

- Nenhuma decisão usa um dado com `available_at` posterior ao instante da decisão. Ordens geradas após o fechamento não recebem fill nesse fechamento.
- O mesmo snapshot, configuração, versão de código e seed produzem o mesmo resultado; mudanças entram em novo manifesto.
- Benchmark, custos, calendário, universo e tratamento de dividendos são definidos antes de comparar estratégias. Métricas brutas e líquidas aparecem lado a lado.
- Cada tentativa de estratégia ou ajuste de parâmetro fica registrada. O período de teste final não serve para escolher parâmetros; se for consultado para isso, deixa de ser teste final.
- Incerteza estatística usa método adequado à dependência temporal e ao tamanho da amostra. Não usar um p-valor isolado como prova de vantagem econômica.
- Dados sintéticos testam software e causalidade. Resultados de ações B3 exigem fonte, direitos e auditoria próprios.
- Para ML, fatores respeitam `available_at ≤ decision_at`; rótulos dependem apenas do futuro usado no treino e nunca entram como informação de decisão. A janela final reservada não serve para selecionar fatores, modelo, limiar ou calibração.

## Próxima entrega concreta

A F1 sintética agora inclui a [terceira formação com cálculo manual](contrato-f1-terceira-formacao.md), um quarto ciclo de regressão e [deslistagem declarada ou incompleta](contrato-f1-deslistagem-sintetica.md). Os [esquemas 4](artefatos-f1-v4.md) e [5](artefatos-f1-v5.md) persistem os ciclos e seus eventos para replay. A revisão de 04/11 continua coberta pelos testes; a sondagem yfinance permanece exploratória e fora do backtest causal.

**Próximo marco — dados e avaliação temporal:** o [protocolo v1](protocolo-pesquisa-f2-v1.md), a [auditoria causal](auditoria-f2-v1.md), os [controles](controles-f2-v1.md), a [sensibilidade a custos](sensibilidade-custos-f2-v1.md) e o [resumo descritivo](resumo-f2-v1.md) cobrem o corte sintético. O [acompanhamento do projeto](status-projeto.md) separa commits publicados, esta entrega local e validação de mercado pendente. Os quatro ciclos sintéticos não bastam para separação temporal útil ou inferência de desempenho; a próxima etapa exige dados licenciados, auditados e com histórico suficiente.

Nenhum resultado sintético ou de cobertura da API demonstra desempenho de ações B3. A numeração desta sequência organiza competências; para os critérios técnicos de aceite F0–F4, prevalece a tabela da especificação técnica.
