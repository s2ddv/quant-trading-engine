# QTRE — estado do projeto

Atualizado em 06/11/2026 (America/Sao_Paulo). Base examinada: branch
`codex/quant-research-environment`, commit `93d8dd9`. O resumo F2 desta entrega
está em uma branch local separada, `codex/f2-summary-doc-reconcile`; esta página
não afirma que ele foi publicado. A [especificação técnica](especificacao-tecnica.md)
continua sendo o contrato de aceite.

| Etapa | Estado | Evidência e limite |
|---|---|---|
| F0 — contratos causais | CONCLUÍDA no sintético | Snapshot, disponibilidade temporal, universo datado e fixtures testados. |
| F1 — motor Python e replay | CONCLUÍDA no sintético | Quatro decisões mensais, ordens, fills, eventos, livro, NAV e replay independente com testes. |
| F2 — protocolo e auditoria causal | CONCLUÍDA no sintético | [Protocolo](protocolo-pesquisa-f2-v1.md) e [auditoria](auditoria-f2-v1.md) versionados; fixture com vazamento é rejeitada. |
| F2 — controles | CONCLUÍDA no sintético | [`cash` e `equal_weight`](controles-f2-v1.md) têm execução, identidade, artefatos e replay próprios. |
| F2 — sensibilidade a custos | CONCLUÍDA no sintético | [Nove cenários](sensibilidade-custos-f2-v1.md), replay e auditoria. Monotonicidade é condicional a fills e agenda comparáveis. |
| F2 — resumo descritivo | CONCLUÍDA localmente; não publicada | [Módulo, teste e contrato](resumo-f2-v1.md) revisados nesta entrega. Custos e cobertura são descritivos; NAV incompleto impede retorno acumulado. |
| F2 — inferência e walk-forward | PARCIAL | Método previsto; quatro ciclos fictícios não fornecem histórico suficiente para separação temporal ou significância. |
| F3/F4 — mercado brasileiro | PARCIAL | Sondagem yfinance é exploratória. Faltam fonte e direitos, universo histórico, eventos, disponibilidade, benchmark e validação fora da amostra. |
| ML supervisionado | PARCIAL, planejamento | Hipótese e regras causais constam do roteiro. Não há dados adequados, treino ou modelo validado. |

## Estado de publicação e verificação

O commit `93d8dd9` está na branch remota
`origin/codex/quant-research-environment`. O [run hospedado
42221699255](https://github.com/s2ddv/quant-trading-engine/actions/runs/42221699255)
terminou com sucesso para Python 3.10 e 3.14 nesse commit, incluindo lint,
testes originais e reprodução do experimento sintético. Esse run precede o resumo
F2 local e não o valida. As alterações locais de outra task no checkout
compartilhado não fazem parte desta entrega.

Os testes desta entrega e o estado final do Git devem ser informados no relatório
final; uma execução de CI antiga não substitui `make check` após as mudanças.
Nenhum resultado sintético ou sondagem de fornecedor demonstra desempenho B3.

## Próximo passo

Auditar uma fonte histórica adequada antes de qualquer avaliação de mercado.
Definir cortes cronológicos, universo e benchmark datados; registrar tentativas e
reservar a janela final. A fase de ML precisará acrescentar fatores disponíveis
na decisão, rótulos futuros com purga nos cortes, treino e validação separados,
baseline momentum e comparação líquida sob o mesmo motor e custos.
