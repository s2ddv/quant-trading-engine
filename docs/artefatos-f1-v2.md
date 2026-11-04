# Artefatos F1 — esquema 2 para segunda formação (histórico)

O esquema 2 conserva os sete arquivos e a serialização do
[esquema 1](artefatos-f1-v1.md). `manifest.json` traz
`artifact_schema_version: 2`; o manifesto do motor usa `schema_version: 3`
e acrescenta `second_decision_at`, `second_formation_session` e
`decision_windows`, com as sessões de execução de cada decisão. O `run_id`
inclui esses campos. Execuções antigas no esquema 1 continuam legíveis.

`orders.jsonl` inclui `formation_id: "second"` nas ordens da segunda decisão.
`side` aceita `buy` e `sell`. `fills.jsonl` das vendas inclui `side: "sell"`,
`cash_credit`, `basis_removed` e `realized_pnl`. Fills de compra da segunda
decisão incluem `side: "buy"` e `cash_debit`; os da primeira formação preservam
o formato original. `ledger.jsonl` acrescenta `kind: "sell"`, com
`cash_delta` positivo e quantidade/base de custo após a venda. `nav.jsonl`
inclui a marcação de 28/02, que sustenta o segundo dimensionamento, entre a
primeira janela de execução e a segunda.

Uma venda usa preço `abertura × (1 − spread − slippage)` e credita
`notional − taxa`. Para venda parcial, `basis_removed` é a base total anterior
vezes a fração da posição vendida, arredondada ao centavo. Venda integral
remove o saldo exato da base para não deixar resíduo. `realized_pnl` é
`cash_credit − basis_removed`. O replay recalcula essas identidades, posição,
caixa, base e NAV a partir do snapshot e dos eventos; verifica calendário,
lotes, capacidade, negociação permitida e que nenhuma compra use caixa futuro.

O esquema 2 demonstra duas decisões, não um laço mensal geral. A continuação
exige NAV completo em 05/02, mas agora conserva dividendos a receber até a
data de pagamento, inclusive quando ela cai na segunda janela. O recebível
integra o NAV sem compor o caixa disponível para compras. O replay reconstrói
o pagamento com os mesmos eventos; não foi necessário mudar o esquema. O
[exemplo manual](contrato-f1-recebivel-entre-formacoes.md) fixa os saldos.
Ações corporativas com ex-data entre 05/02 e 28/02 eram rejeitadas nesta
versão; o [esquema 3](artefatos-f1-v3.md) registra as sessões intermediárias.
Suspensão
durante a janela bloqueia fill, saldo de ordem vence após três sessões e
eventos corporativos na janela usam as regras existentes. Não há vendas reais,
liquidação B3, custos observados ou autenticação externa do manifesto. Sinais
continuam em memória; as ordens persistidas registram suas chaves de entrada.
