# Quant Trading Research Engine

Motor de pesquisa quantitativa para testar, futuramente, momentum cross-sectional 12–2 em ações B3. A [especificação técnica](docs/especificacao-tecnica.md) define os contratos do motor; o [plano de competências e entregas](docs/roadmap-competencias.md) organiza a evolução como projeto de portfólio. Há um protótipo sintético de sinal, execução e contabilidade e uma sondagem exploratória via yfinance. Ainda não há backtest validado com dados B3.

## Estado: F1 parcial — uma formação sintética

O parser em `src/qtre/data/snapshot.py` valida snapshots JSON de esquema `1` e calcula SHA-256 dos bytes JSON canônicos (chaves ordenadas, sem espaços). Entradas com o mesmo conteúdo produzem o mesmo hash. Os registros são congelados após a leitura. O calendário é uma lista explícita de sessões sintéticas no fuso `America/Sao_Paulo`; seus horários UTC não representam um calendário oficial da B3.

Contratos incluídos: `PriceBar` bruto, `OpenEvent`, `CorporateAction`, `UniverseMembership` e histórico de ticker por `instrument_id`. Cada registro tem origem e os três relógios `observed_at`, `available_at` e `ingested_at`. `Snapshot.available(collection, as_of)` retorna somente registros conhecidos até o corte. O parser rejeita chaves ou registros duplicados, timestamps sem fuso, OHLC inválido, intervalos sobrepostos, barras completas antes do fechamento e dados posteriores ao `as_of` do snapshot.

As fixtures F0 em `examples/` são pequenas e controladas. A F1 acrescenta `synthetic_f1_v1.json`, com 14 meses e cinco instrumentos fictícios. `qtre.universe.listed_members` reconstrói membros datados; `qtre.signals.momentum_12_2` aplica o corte de disponibilidade e calcula o score. `qtre.backtest.run_f1` demonstra uma formação mensal, ordens para a abertura seguinte, fills com custos hipotéticos, split, dividendo, suspensão, livro e NAV. O [contrato sintético da F1](docs/contrato-f1-sintetico.md) fixa entradas e valores esperados. Isto verifica a mecânica do software; não mede desempenho de ações brasileiras.

`qtre.reporting.write_f1_run` grava uma execução em diretório novo escolhido pelo chamador; `qtre.reporting.replay_f1` valida hashes e reconstrói caixa, posições, recebíveis e NAV lendo apenas os arquivos, sem executar `run_f1`. O [esquema dos artefatos F1](docs/artefatos-f1-v1.md) descreve formato, limites e conciliação. Exemplo sintético:

```python
from datetime import datetime, timezone
from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot
from qtre.reporting import write_f1_run, replay_f1

snapshot = load_snapshot("examples/synthetic_f1_v1.json")
result = run_f1(snapshot, decision_at=datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc))
write_f1_run(snapshot, result, "/tmp/qtre-f1-example")
reconstructed = replay_f1("/tmp/qtre-f1-example")
```

Escolha outro diretório quando o anterior já existir: a gravação recusa substituição silenciosa.

## Executar a validação

Requer Python 3.10+; o núcleo e a suíte de testes usam apenas a biblioteca padrão. A consulta real é uma dependência opcional.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -c 'from qtre import load_snapshot; print(load_snapshot("examples/synthetic_normal_v1.json").content_hash)'
```

Para regenerar as fixtures: `python3 examples/generate_fixtures.py` e `python3 examples/generate_f1_fixture.py`. Cada script sobrescreve somente seus próprios arquivos JSON sintéticos em `examples/`.

A fixture F1 grava um registro por linha para facilitar revisão sem alterar seu conteúdo canônico. Veja a [revisão de 04/11/2026](docs/revisao-f1-2026-11-04.md) para falhas corrigidas anteriormente. A F1 ainda não possui rebalanceamentos sucessivos ou vendas.

O hash identifica o conteúdo validado do snapshot. Ele não demonstra autenticidade de fornecedor, licença de dados, calendário oficial ou ausência de viés; esses pontos pertencem às fases F3/F4.

## Sondagem exploratória com yfinance

O adaptador opcional consulta OHLC do fornecedor, volume, dividendos e splits via `yfinance` e imprime um resumo de cobertura, sem gravar preços no repositório. `auto_adjust=False` desativa o ajuste automático adicional da biblioteca; não certifica que os valores sejam os preços originais negociados:

```bash
pip install -e '.[yahoo]'
PYTHONPATH=src python3 -m qtre.data.yfinance_probe --start 2024-01-01 --end 2025-03-01
```

Por padrão, consulta `PETR4.SA`, `VALE3.SA`, `ITUB4.SA`, `BBDC4.SA` e `ABEV3.SA`. O intervalo final é exclusivo. `keepna=True` preserva as linhas faltantes retornadas pelo fornecedor para auditoria. A saída verifica finitude/coerência OHLC, volumes, ações, duplicatas, ordenação e datas fora do intervalo. Volume zero recebe `REVIEW`; dado inválido recebe `INCOMPLETE`; falha de consulta recebe `FETCH_ERROR`. O comando termina com código 2 em caso de falha ou dados incompletos.

A contagem de linhas não comprova cobertura de um calendário oficial. O adaptador **não** cria `Snapshot` causal nem alimenta o backtest F1: a resposta histórica não fornece `available_at` e revisões por registro, calendário oficial versionado, universo histórico com saídas ou evento de abertura com horário de publicação verificado. A coorte de cinco tickers foi escolhida hoje e não demonstra ausência de viés de sobrevivência.
