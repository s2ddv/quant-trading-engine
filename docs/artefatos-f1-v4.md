# Artefatos F1 — esquema 4 para ciclos mensais

O esquema 4 conserva os sete arquivos e a serialização decimal/temporal dos
esquemas anteriores. `artifact_schema_version` passa a `4`; o manifesto do
motor usa `schema_version: 5` e `decision_windows` com três ou mais janelas.
Cada janela registra `decision_at`, `formation_session`, `bridge_sessions`,
`execution_sessions` e `portfolio_reason`. A primeira ponte é vazia; as
seguintes cobrem todas as sessões desde o fim da execução anterior até a
formação seguinte. Os IDs `O3-...`, `O4-...` etc. separam ordens e fills por
ciclo. O replay valida a sequência contra o calendário do snapshot e
reconstrói cada NAV sem chamar o motor. Os esquemas 1 a 3 continuam legíveis.

O [exemplo manual da terceira formação](contrato-f1-terceira-formacao.md)
fixa NAV de R$ 101.255,20 antes das ordens e R$ 101.248,25 após seus custos.
Um quarto ciclo sintético gerado no teste verifica a repetição. Com menos de
cinco nomes elegíveis, o alvo vira caixa e são emitidas vendas das posições
existentes; suspensão ou capacidade insuficiente podem impedir a liquidação
integral. A venda total remove a base de custo exata, sem resíduo de centavos.

Este formato ainda usa hipóteses sintéticas de abertura, custos, calendário e
liquidação imediata. Não é um resultado B3 nem valida uma estratégia.
