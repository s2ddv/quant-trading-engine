# Artefatos F1 — esquema 5 para deslistagem com dinheiro declarado

O snapshot de [esquema 2](contrato-snapshot-v2.md) pode declarar, em uma ação
`delisting`, `exit_cash_per_share` e `pay_session`. Quando há posição na
ex-data, o livro registra `delisting_ex`: quantidade e base de custo caem a
zero, `basis_removed` conserva a base integral e `realized_pnl` é o valor a
receber menos essa base. `delisting_pay` troca o recebível por caixa na data
de pagamento. Nenhum desses eventos é um fill em bolsa.

Execuções que contêm `delisting_ex` têm `event_schema_version: 2` no
manifesto do motor e `artifact_schema_version: 5` no envelope. O `run_id`
inclui o campo novo. O replay verifica o valor por ação contra o snapshot,
a base removida, o resultado realizado, o pagamento e a cobertura do evento.
O [exemplo sintético](contrato-f1-deslistagem-sintetica.md) fixa R$ 10.530,00
de recebível e R$ 4.445,89 de resultado realizado. Sem valor de saída
declarado, a posição e sua base ficam no livro com `NAV_INCOMPLETO`; uma nova
decisão exige NAV completo. Os esquemas 1 a 4 continuam legíveis.

O valor de saída da fixture é uma hipótese controlada. Dados reais exigem
fonte, vigência, direito econômico e prazo de pagamento verificáveis.
