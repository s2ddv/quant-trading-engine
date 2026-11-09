# Contrato de auditoria de fonte histórica B3 — v1

**Registro prévio à avaliação de candidatos:** 09/11/2026, America/Sao_Paulo. **Escopo:** prontidão de dados para futura pesquisa de momentum 12–2; nenhuma execução de mercado, treino ou alteração do motor. A hipótese operacional é que ao menos uma fonte documentada possa fornecer dados com direitos e proveniência suficientes para reconstruir decisões passadas. A hipótese nula é que essa capacidade ainda não foi demonstrada. Unidade de inspeção: fonte, produto/campo e amostra por instrumento e sessão; não há métrica de retorno nesta auditoria. Baseline de comparação: contrato causal do QTRE, não desempenho de carteira.

## Evidência e decisão

Para cada campo, distinguir **documentado** (página oficial/contrato que o promete), **observado em amostra** (extração autorizada, identificada e verificável) e **não demonstrado**. Guardar URL, título, entidade, data da consulta, trecho ou fato observado e limites da inferência. Uma página comercial não substitui contrato de licença; uma API que retorna barras atuais não prova histórico point-in-time. `apta` requer documentação e amostra verificadas em todos os itens críticos abaixo. `apta com restrições` exige direitos claros e amostra reproduzível, com lacunas delimitadas que não contaminem a pergunta causal autorizada. Sem esses requisitos, usar `não demonstrada`; não iniciar F3/F4 causal.

## Critérios de aceite, fixados antes da avaliação

| ID | Exigência e teste de amostra planejado | Bloqueio causal se faltar |
|---|---|---|
| C1 | Direito explícito de acesso, uso em pesquisa, armazenamento de snapshot/hash, reprodução por revisor e publicação de agregados; identificar licença, produto, versão e restrições de redistribuição. | Sem direito de guardar/reproduzir, a pesquisa não é auditável. |
| C2 | Série diária que cubra ao menos 13 fechamentos mensais consecutivos antes de cada decisão e janelas futuras de desenvolvimento, validação e teste reservadas; mapear datas inicial/final, sessões faltantes e instrumentos deslistados. | Histórico curto ou coorte sobrevivente impede formação ou introduz viés. |
| C3 | `instrument_id` persistente distinto do ticker; cadastro com símbolo, classe, listagem, suspensão, sucessão e `valid_from`/`valid_to`, incluindo entradas e saídas históricas. Reconstruir manualmente datas amostradas. | Ticker atual e universo atual não reconstroem elegibilidade passada. |
| C4 | OHLC e volumes brutos em ações/BRL, abertura negociável separada da barra completa, moeda/unidade, metodologia de ajustes e revisão de registros; testar sessões, duplicatas, não finitos, OHLC e volume. | Série ajustada retrospectivamente ou barra final usada na abertura vaza futuro. |
| C5 | Eventos corporativos com identificador, tipo, anúncio/publicação, ex-date, record/pay date, razão/valor e correções; conferir splits, proventos e deslistagens contra documentos datados. | Retorno total, quantidade, caixa e NAV podem ficar incorretos. |
| C6 | `observed_at` (fato), `available_at` (primeira publicação verificável), `ingested_at` (captura local), fuso e histórico de revisões por versão. Testar `available_at <= decision_at` e ordem anterior ao fill na próxima abertura. | Data da sessão ou hora da coleta atual não prova disponibilidade passada; `availability_assumed` limita a conclusão. |
| C7 | Calendário de pregões e sessões especiais datado; liquidez histórica (`volume_brl`, volume em ações e faltas) e regra para suspensões, leilões e ausência de abertura. | Elegibilidade e execução não são reconstruíveis. |
| C8 | Benchmark investível com metodologia, constituintes ou nível/retorno total e vigência datados, mesma moeda/calendário; custos e regras de negociação históricos documentáveis em fonte complementar. | Não há comparação líquida equivalente. |
| C9 | Versão imutável ou captura permitida com hash por arquivo/registro, manifesto de origem, intervalo, consulta, esquema, timezone e correções; repetir consulta e explicar diferenças. | Replay de bytes sozinho não atesta origem nem história de revisões. |

## Protocolo posterior, sem coleta nesta versão

Solicitar amostra pequena e legalmente autorizada que inclua uma ação ativa, uma deslistada, mudança de ticker, split, provento, suspensão e correção publicada; selecionar datas antes de olhar retornos. Guardar apenas manifestos, hashes e contagens em `docs/`; dados licenciados ficam fora do Git. Confrontar com comunicados oficiais e calendário. Antes de qualquer backtest, congelar fonte, universo, regras, custos, benchmark e cortes temporais em novo protocolo; preservar a janela final. Nenhuma lacuna pode ser preenchida por `available_at` retroativo presumido sem rótulo de viés e sem restringir a conclusão.

Referências internas: [especificação](especificacao-tecnica.md), [roadmap](roadmap-competencias.md), [estado](status-projeto.md), [protocolo F2](protocolo-pesquisa-f2-v1.md) e [sondagem exploratória](sondagem-yfinance-2026-11-04.md).
