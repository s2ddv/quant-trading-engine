# Quant Trading Research Engine

A quantitative research engine for investigating 12–2 cross-sectional momentum in B3 equities. The [technical specification](docs/especificacao-tecnica.md) defines the engine contracts, and the [research roadmap](docs/roadmap-competencias.md) tracks the planned work. The repository currently contains synthetic signal, execution, accounting, and independent replay examples, plus an exploratory `yfinance` data probe. **There is no validated backtest using B3 market data.**

## Current status: synthetic F1 research prototype

The parser in `src/qtre/data/snapshot.py` validates schema-1 JSON snapshots and computes SHA-256 over canonical JSON bytes (sorted keys, no whitespace). Identical content yields the same hash, and parsed records are frozen. The calendar is an explicit list of synthetic sessions in `America/Sao_Paulo`; its UTC times are not an official B3 calendar.

The data contracts include raw `PriceBar` records, `OpenEvent`, `CorporateAction`, `UniverseMembership`, and ticker history keyed by `instrument_id`. Each record includes provenance and three timestamps: `observed_at`, `available_at`, and `ingested_at`. `Snapshot.available(collection, as_of)` returns only records known by the cutoff. The parser rejects duplicate keys or records, timezone-naive timestamps, invalid OHLC values, overlapping intervals, complete bars before the close, and data later than the snapshot's `as_of`.

The small F0 fixtures in `examples/` test these contracts. F1 adds `synthetic_f1_v1.json`, with 14 months and five fictional instruments. `qtre.universe.listed_members` reconstructs dated membership, and `qtre.signals.momentum_12_2` applies the availability cutoff and calculates scores. `qtre.backtest.run_f1` demonstrates one monthly decision, orders for the next open, fills with hypothetical costs, a split, a dividend, a suspension, accounting entries, and NAV. The [synthetic F1 contract](docs/contrato-f1-sintetico.md) specifies the inputs and expected values. These examples verify software mechanics, not Brazilian equity performance.

`qtre.reporting.write_f1_run` writes a run to a new caller-selected directory. `qtre.reporting.replay_f1` verifies hashes and reconstructs cash, positions, receivables, and NAV from the saved files without calling `run_f1`. See the [F1 artifact schema](docs/artefatos-f1-v1.md) for file formats and reconciliation rules.

```python
from datetime import datetime, timezone
from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot
from qtre.reporting import replay_f1, write_f1_run

snapshot = load_snapshot("examples/synthetic_f1_v1.json")
result = run_f1(snapshot, decision_at=datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc))
write_f1_run(snapshot, result, "/tmp/qtre-f1-example")
reconstructed = replay_f1("/tmp/qtre-f1-example")
```

The [second synthetic formation](docs/contrato-f1-segunda-formacao.md) adds a sale, purchases after that sale, and reconciled NAV. `run_f1_two_formations` runs the January 31 and February 28 decisions on `synthetic_f1_rebalance_v1.json`. Saved runs can be replayed independently. The [intermediate-session contract](docs/contrato-f1-sessoes-intermediarias.md) extends this example with daily marks and corporate actions between decisions, including a dividend receivable carried until payment; see [artifact schema 3](docs/artefatos-f1-v3.md). For the two-decision example, pass the dates from the [manual contract](docs/contrato-f1-segunda-formacao.md) as `first_decision_at` and `second_decision_at`, then pass the result to `write_f1_run` and its output directory to `replay_f1`.

A [third-formation contract](docs/contrato-f1-terceira-formacao.md) and synthetic fixture describe a March decision. A local monthly-cycle implementation is under development; the stable documented examples above remain the reference for completed F1 behavior. General monthly processing and explicit resolved-delisting rules are still pending. Choose a new output directory for each run: artifact writing refuses to silently replace an existing directory.

## Run the validation suite

Python 3.10+ is required. The core engine and tests use only the standard library; live data probing is optional.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -c 'from qtre import load_snapshot; print(load_snapshot("examples/synthetic_normal_v1.json").content_hash)'
```

To regenerate synthetic fixtures, run `python3 examples/generate_fixtures.py`, `python3 examples/generate_f1_fixture.py`, and `python3 examples/generate_f1_rebalance_fixture.py`. Each script overwrites only its own synthetic JSON files in `examples/`. The F1 fixture uses one record per line to ease review without changing its canonical content. The [November 4, 2026 review](docs/revisao-f1-2026-11-04.md) records previously corrected failures.

A snapshot hash identifies validated content. It does not establish vendor authenticity, data rights, an official calendar, or freedom from bias. Those concerns belong to later research and data-integration phases.

## Exploratory `yfinance` probe

The optional adapter requests vendor OHLC data, volume, dividends, and splits, then prints a coverage summary without saving market prices in this repository. `auto_adjust=False` disables additional automatic adjustment by the library; it does not certify that returned values are original traded prices.

```bash
pip install -e '.[yahoo]'
PYTHONPATH=src python3 -m qtre.data.yfinance_probe --start 2024-01-01 --end 2025-03-01
```

By default, the probe requests `PETR4.SA`, `VALE3.SA`, `ITUB4.SA`, `BBDC4.SA`, and `ABEV3.SA`. The end date is exclusive. `keepna=True` preserves missing rows returned by the vendor for review. Output checks OHLC finiteness and consistency, volume, corporate actions, duplicates, ordering, and dates outside the requested interval. Zero volume is marked `REVIEW`, invalid data `INCOMPLETE`, and request failures `FETCH_ERROR`. The command exits with code 2 on a failed request or incomplete data.

A row count cannot establish coverage against an official exchange calendar. The probe does **not** create a causal `Snapshot` or feed the F1 backtest. Its historical response does not provide per-record `available_at` timestamps and revisions, a versioned official calendar, a historical universe including delistings, or opening events with verified publication times. The five-ticker cohort was selected in the present and does not rule out survivorship bias.
