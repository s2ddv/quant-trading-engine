# Quant Trading Research Engine

Motor de pesquisa quantitativa para testar, futuramente, momentum cross-sectional 12–2 em ações B3. A [especificação técnica](docs/especificacao-tecnica.md) define os contratos do motor; o [plano de competências e entregas](docs/roadmap-competencias.md) organiza a evolução como projeto de portfólio. Ainda não há backtest, estratégia implementada ou resultado com dados B3.

## Estado: F0 — contratos e dados sintéticos

O parser em `src/qtre/data/snapshot.py` valida snapshots JSON de esquema `1` e calcula SHA-256 dos bytes JSON canônicos (chaves ordenadas, sem espaços). Entradas com o mesmo conteúdo produzem o mesmo hash. Os registros são congelados após a leitura. O calendário é uma lista explícita de sessões sintéticas no fuso `America/Sao_Paulo`; seus horários UTC não representam um calendário oficial da B3.

Contratos incluídos: `PriceBar` bruto, `OpenEvent`, `CorporateAction`, `UniverseMembership` e histórico de ticker por `instrument_id`. Cada registro tem origem e os três relógios `observed_at`, `available_at` e `ingested_at`. `Snapshot.available(collection, as_of)` retorna somente registros conhecidos até o corte. O parser rejeita chaves ou registros duplicados, timestamps sem fuso, OHLC inválido, intervalos sobrepostos, barras completas antes do fechamento e dados posteriores ao `as_of` do snapshot.

As fixtures em `examples/` são pequenas e controladas. A normal tem dois instrumentos e três sessões. A adversa acrescenta split, dividendo, abertura suspensa e barra ausente. A F1 ampliará o histórico para 13+ meses e 5+ ativos, necessário para testar o sinal 12–2.

## Executar a validação

Requer Python 3.10+; o núcleo F0 usa apenas a biblioteca padrão.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -c 'from qtre import load_snapshot; print(load_snapshot("examples/synthetic_normal_v1.json").content_hash)'
```

Para regenerar as duas fixtures: `python3 examples/generate_fixtures.py`. Isso sobrescreve apenas os dois arquivos JSON sintéticos em `examples/`.

O hash identifica o conteúdo validado do snapshot. Ele não demonstra autenticidade de fornecedor, licença de dados, calendário oficial ou ausência de viés; esses pontos pertencem às fases F3/F4.
