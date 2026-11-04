# Quant Trading Research Engine

Motor de pesquisa quantitativa para testar, futuramente, momentum cross-sectional 12–2 em ações B3. A [especificação técnica](docs/especificacao-tecnica.md) define os contratos do motor; o [plano de competências e entregas](docs/roadmap-competencias.md) organiza a evolução como projeto de portfólio. Ainda não há backtest, estratégia implementada ou resultado com dados B3.

## Estado: F1 — corte vertical sintético

O parser em `src/qtre/data/snapshot.py` valida snapshots JSON de esquema `1` e calcula SHA-256 dos bytes JSON canônicos (chaves ordenadas, sem espaços). Entradas com o mesmo conteúdo produzem o mesmo hash. Os registros são congelados após a leitura. O calendário é uma lista explícita de sessões sintéticas no fuso `America/Sao_Paulo`; seus horários UTC não representam um calendário oficial da B3.

Contratos incluídos: `PriceBar` bruto, `OpenEvent`, `CorporateAction`, `UniverseMembership` e histórico de ticker por `instrument_id`. Cada registro tem origem e os três relógios `observed_at`, `available_at` e `ingested_at`. `Snapshot.available(collection, as_of)` retorna somente registros conhecidos até o corte. O parser rejeita chaves ou registros duplicados, timestamps sem fuso, OHLC inválido, intervalos sobrepostos, barras completas antes do fechamento e dados posteriores ao `as_of` do snapshot.

As fixtures F0 em `examples/` são pequenas e controladas. A F1 acrescenta `synthetic_f1_v1.json`, com 14 meses e cinco instrumentos fictícios. `qtre.universe.listed_members` reconstrói membros datados; `qtre.signals.momentum_12_2` aplica o corte de disponibilidade e calcula o score. `qtre.backtest.run_f1` demonstra uma formação mensal, ordens para a abertura seguinte, fills com custos hipotéticos, split, dividendo, suspensão, livro e NAV. O [contrato sintético da F1](docs/contrato-f1-sintetico.md) fixa entradas e valores esperados. Isto verifica a mecânica do software; não mede desempenho de ações brasileiras.

## Executar a validação

Requer Python 3.10+; o núcleo F0 usa apenas a biblioteca padrão.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -c 'from qtre import load_snapshot; print(load_snapshot("examples/synthetic_normal_v1.json").content_hash)'
```

Para regenerar as fixtures: `python3 examples/generate_fixtures.py` e `python3 examples/generate_f1_fixture.py`. Cada script sobrescreve somente seus próprios arquivos JSON sintéticos em `examples/`.

O hash identifica o conteúdo validado do snapshot. Ele não demonstra autenticidade de fornecedor, licença de dados, calendário oficial ou ausência de viés; esses pontos pertencem às fases F3/F4.
