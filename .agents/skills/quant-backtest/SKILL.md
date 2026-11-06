---
name: quant-backtest
description: Validate QTRE backtest causality, execution costs, accounting, controls, and out-of-sample protocols when implementing, auditing, or interpreting a backtest.
---

# Quant Backtest

Read `AGENTS.md`, `docs/protocolo-pesquisa-f2-v1.md`, and the snapshot and artifact contracts relevant to the run. Existing F1/F2 artifacts are synthetic; the yfinance probe is exploratory, not a point-in-time research snapshot.

## Workflow

1. Freeze the strategy/configuration and enumerate data lineage, historical membership, suspensions, corporate actions, delistings, and publication delays. Identify survivorship and selection filters. Missing historical provenance is a limitation, not permission to infer availability.
2. Trace each input from event time through `available_at` to decision, order, next eligible open, fill, and valuation. Future observations may change later fills or marks, but must not rewrite prior decisions. Hash equality proves byte integrity; semantic temporal auditing must also pass.
3. Hand-reconcile quantity, price, lot rounding, capacity, spread, slippage, fees, cash, cost basis, receivables, positions, and NAV on a small fixture. Preserve existing money/rounding conventions. Unknown marks or unresolved delistings must retain incomplete NAV rather than becoming zero returns.
4. Model costs by side and units (bps versus BRL), with explicit liquidity/market-impact assumptions and capacity limits. Do not infer realistic B3 execution from synthetic cost settings. Compare cost monotonicity only with the same fill schedule and quantities; higher costs can alter feasibility and trades.
5. Compare strategy and controls using their own auditable artifacts and the same decision information and execution rules. Attribute gross-to-net effects to trading costs, holdings, cash, and corporate events without double counting; reconcile the attribution back to ledger/NAV.
6. For real research, freeze chronological out-of-sample and walk-forward protocols before outcomes, including purge/embargo and benchmark availability. Report trial count and selection procedure. Current four-cycle fixtures have no validated out-of-sample performance.
7. Run independent replay and causal audit, including adversarial future-information inputs. Report failures and incomplete metrics explicitly before summarizing returns or risk.

## Expected outputs

- A timeline and provenance audit, hand-calculated ledger reconciliation, and executable checks.
- A report of controls, costs, execution assumptions, attribution, coverage, exclusions, and incomplete NAV.
- Reproduction commands and clear separation between synthetic mechanical validation and market evidence.

## Practical validation example

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f2_audit.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f1_backtest.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f2_cost_sensitivity.py' -v
```

Check that a future bar in order inputs is rejected even after valid rehashing; next-open execution reconciles to cents; changed fill quantity prevents a cost-monotonicity claim. These negative tests are part of the expected successful outcome.
