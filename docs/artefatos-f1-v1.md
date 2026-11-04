# Artefatos da execução sintética F1 — esquema 1

`write_f1_run(snapshot, result, directory)` cria exclusivamente um diretório novo.
`replay_f1(directory)` lê a cópia de `snapshot.json`, `manifest.json` e as
tabelas persistidas; não executa sinal, carteira nem `run_f1`.

| Arquivo | Conteúdo e chave |
|---|---|
| `snapshot.json` | Snapshot F0 canônico, validado novamente no replay. |
| `manifest.json` | `artifact_schema_version: 1`, manifesto F1 original, `files` com SHA-256 de cada outro arquivo. |
| `orders.jsonl` | Ordens originais, chave `order_id`; `run_id` em cada linha. |
| `order_states.jsonl` | Estado terminal por `order_id`; `run_id` em cada linha. |
| `fills.jsonl` | Execuções, chave `fill_id`; `run_id` em cada linha. |
| `ledger.jsonl` | Lançamentos na ordem de processamento, chave `event_id`; `run_id` em cada linha. |
| `nav.jsonl` | Uma marcação por sessão, chave `session`; `run_id` em cada linha. |

Campos do esquema 1 (além de `run_id` nas tabelas):

- Manifesto: `artifact_schema_version`, `run` (o manifesto F1 completo, com
  `schema_version`, `synthetic`, `snapshot_hash`, `calendar_id`, `code_hash`,
  `model_id`, `python_version`, `decimal_precision`, `monetary_rounding`,
  `settlement`, `formation_session`, `decision_at`, `config`, `run_id`) e
  `files` (mapa de nome para SHA-256).
- Ordem: `order_id`, `instrument_id`, `created_at`, `earliest_execution_at`,
  `side`, `quantity`, `target_weight`, `expiry_session`, `reference_session`,
  `reference_price`, `capacity_shares`, `input_keys`.
- Estado da ordem: `order_id`, `instrument_id`, `remaining`, `filled`, `status`,
  `reason`.
- Fill: `fill_id`, `order_id`, `instrument_id`, `executed_at`, `session`,
  `quantity`, `price`, `reference_price`, `reference_notional`,
  `notional_brl`, `spread_cost`, `slippage_cost`, `fees`, `cash_debit`,
  `source_key`, `input_available_at`, `model_id`.
- Lançamento: `event_id`, `session`, `kind`, `instrument_id`, `quantity`,
  `cost_basis`, `cash_delta`, `cash_brl`, `receivable_brl`.
- NAV: `session`, `valued_at`, `status`, `cash_brl`, `receivable_brl`,
  `positions_value_brl`, `nav_brl`, `missing_marks`, `marks`. Cada marca traz
  `quantity`, `price`, `source_key` e usa `instrument_id` como chave.

JSON UTF-8 usa chaves ordenadas, separadores compactos e newline final. Valores
`Decimal` são strings decimais finitas em notação fixa; instantes das tabelas
são strings UTC ISO 8601 terminadas em `Z` (o `decision_at` do manifesto F1
original usa `+00:00`); datas de sessão são `YYYY-MM-DD`; quantidades
são inteiros. Tuplas viram arrays. A ordem das linhas preserva a ordem do motor.
O manifesto lista nomes fixos e hashes dos bytes, inclusive do snapshot. O
`run_id` do motor identifica configuração e código, enquanto os hashes dos
arquivos identificam a saída concreta. Nenhum arquivo existente é substituído.

O replay valida os hashes, a identidade do snapshot e `run_id`, os custos de
cada fill, o vínculo com abertura e ordem, e cada lançamento. Reconstitui
caixa, posição, base de custo e recebíveis a partir de fills e ações do
snapshot, confronta cada estado do livro e recalcula NAV com fechamentos
disponíveis no instante de marcação. Em `NAV_INCOMPLETO`, mantém caixa e
recebíveis auditáveis e não fabrica valor ou retorno para preço ausente.

Escopo: uma formação sintética, compras e liquidação imediata. O esquema 1
não define vendas, lotes, tarifas reais ou recuperação de deslistagem. Uma
alteração de qualquer contrato exige nova versão de esquema.
