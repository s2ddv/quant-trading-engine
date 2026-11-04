# Artefatos F1 — esquema 3 para sessões intermediárias

O esquema 3 conserva os sete arquivos e a representação estável do
[esquema 2](artefatos-f1-v2.md). `manifest.json` passa a ter
`artifact_schema_version: 3`; o manifesto do motor usa `schema_version: 4`,
`model_id: synthetic-f1-two-formations-v2` e `bridge_sessions`, lista ordenada
de todas as sessões após a primeira janela até a segunda formação, inclusive.
O `run_id` inclui esses campos. O leitor continua aceitando os esquemas 1 e 2.

`nav.jsonl` contém uma marca após o fechamento de cada sessão da ponte. O
pagamento de dividendo entre janelas aparece em `ledger.jsonl` como
`dividend_pay` na data de pagamento. Split e dividendo com ex-data na ponte
atualizam quantidade ou recebível antes da marcação; uma deslistagem não
resolvida torna o NAV incompleto. Ações conhecidas depois da abertura de sua
ex-data, quando havia posição, são rejeitadas. O replay verifica a sequência
completa de sessões, reconstrói os eventos e compara o NAV de cada dia. O
[exemplo manual](contrato-f1-sessoes-intermediarias.md) concilia um pagamento
em 10/02 sem criar retorno.

Este incremento ainda usa duas decisões fixas e liquidação sintética imediata.
Não há laço mensal arbitrário, preenchimento retroativo de marca ausente,
regra para deslistagem resolvida nem processamento de ordens pendentes entre
formações. Também não há evidência de desempenho com dados reais.
