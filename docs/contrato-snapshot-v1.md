# Contrato de snapshot sintético v1 (F0)

Este contrato implementa a F0 da [especificação técnica](especificacao-tecnica.md). O parser em `src/qtre/data/snapshot.py` é a definição executável. As duas entradas de referência estão em `examples/`.

## Envelope

`schema_version` é o inteiro `1`; `snapshot_id` é texto não vazio; `as_of` é um instante ISO 8601 com fuso. `calendar` contém `calendar_id`, `timezone` igual a `America/Sao_Paulo` e `sessions` em ordem crescente. Cada sessão tem data `YYYY-MM-DD`, `open_at` e `close_at` com fuso. Ambas as horas devem cair na data local da sessão; sessões não podem se sobrepor nem ultrapassar `as_of`.

As coleções obrigatórias são `bars`, `opens`, `actions`, `memberships` e `symbols`, todas listas que podem estar vazias. Campos desconhecidos são rejeitados para impedir erros silenciosos de digitação. Cada registro inclui `source_id`, `source_version`, `snapshot_id`, `observed_at`, `available_at` e `ingested_at`. Exige-se `observed_at ≤ available_at ≤ ingested_at ≤ as_of`; `snapshot_id` coincide com o envelope. A consulta `available(collection, as_of)` filtra por `available_at`, com corte consciente de fuso e não posterior ao snapshot.

## Registros

| Coleção | Campos adicionais | Regra central |
|---|---|---|
| `bars` | `instrument_id`, `session`, `open`, `high`, `low`, `close`, `volume_shares`, `volume_brl`, `currency`, `adjustment_basis` | OHLC positivo, finito e coerente; volume não negativo; BRL e preço bruto; barra completa observada e disponível após o fechamento. Chave única `(instrument_id, session)`. |
| `opens` | `instrument_id`, `session`, `open_price`, `currency`, `tradable` | Preço positivo, BRL e booleano de negociabilidade; disponibilidade a partir da abertura. Chave única `(instrument_id, session)`. Uma abertura suspensa pode existir sem barra completa. |
| `actions` | `action_id`, `instrument_id`, `kind`, `announced_at`, `ex_session`; por tipo `ratio`, `cash_per_share`, `pay_session` | Tipos aceitos: `split`, `dividend`, `delisting`. Split requer razão positiva; dividendo requer valor não negativo e sessão de pagamento. `action_id` é único. |
| `memberships` | `instrument_id`, `valid_from`, `valid_to`, `status`, `reason` | Status `listed`, `suspended` ou `delisted`. `valid_to` é inclusivo ou `null` para aberto. Intervalos do mesmo instrumento não se sobrepõem. |
| `symbols` | `instrument_id`, `ticker`, `valid_from`, `valid_to` | Histórico de símbolos separado da identidade persistente; intervalos do mesmo instrumento não se sobrepõem. |

Preços são números decimais de entrada e são verificados com `Decimal`; hashes usam a representação JSON canônica original, sem normalizar `10` e `10.0` como iguais. Este contrato valida dados estruturais e disponibilidade temporal. A F1 acrescentará regras econômicas entre registros, contabilidade de ações corporativas, lotes e sinal 12–2.

Regras temporais adicionais: o `observed_at` de uma abertura não pode preceder a abertura da sessão; `ex_session` não pode ser nulo e o pagamento de um dividendo não pode ocorrer antes de sua data ex. A ordem entre eventos corporativos e fills pertence ao consumidor F1.

## Identidade do conteúdo

O `content_hash` é SHA-256 do objeto JSON com chaves ordenadas, UTF-8, sem espaços supérfluos e sem `NaN`/infinito. Ordem das listas é parte do conteúdo; refazer uma fixture com o mesmo conteúdo preserva o hash. Revisão de um registro cria outro hash. O hash não é assinatura de origem nem `run_id` de backtest.
