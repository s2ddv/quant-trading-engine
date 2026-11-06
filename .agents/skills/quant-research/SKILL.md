---
name: quant-research
description: Design or review QTRE research hypotheses, mathematical assumptions, baselines, experiments, and statistical interpretations when proposing or evaluating a quantitative study.
---

# Quant Research

Work from the repository root. Read `AGENTS.md`, `docs/especificacao-tecnica.md`, and the relevant current protocol; F2's frozen method is in `docs/protocolo-pesquisa-f2-v1.md`. Inspect implementation before treating a roadmap item as available.

## Workflow

1. State the economic hypothesis, null hypothesis, observable target, decision time, unit of analysis, and a falsifiable acceptance criterion before inspecting outcomes. Separate a mechanical software claim from a market-performance claim.
2. Write equations with units, return convention, currency, calendar, event/availability timestamps, rounding, and assumptions. Hand-calculate a small example before proposing changes. Changing financial calculations or frozen parameters requires explicit user authorization.
3. Freeze dataset identity, historical universe, date range, code revision, configuration, seeds (or explicitly no randomness), controls, primary metric, and experimental budget. Record every trial, including failed and unfavorable results; do not select only the best trial.
4. Compare against an economically meaningful baseline under comparable availability, costs, capital, and execution constraints. QTRE currently provides synthetic cash and equal-weight controls. Synthetic controls are not verified investible B3 benchmarks.
5. Specify temporal development/validation/test boundaries before accessing the final holdout. Use walk-forward evaluation only when sufficient history exists; account for overlapping labels and dependent observations. Preserve F2's existing embargo unless a separately approved protocol revision changes it.
6. Interpret effect size, uncertainty, power, sample size, and multiple comparisons together. Use time-series-appropriate uncertainty methods when justified; do not apply an IID test or annualization automatically. Treat selection on repeated trials as evidence requiring correction or fresh data.
7. Publish inputs, command, artifacts, exclusions, negative findings, and reproducibility limits. Four synthetic cycles demonstrate mechanics only; they cannot substantiate profitability, Sharpe, or statistical significance.

## Expected outputs

- A preregistered experiment specification with hypothesis, equations, units, baselines, temporal splits, and acceptance/rejection rules.
- A reproducibility record tying data and code identities to configuration, all trials, metrics, and artifacts.
- A conclusion labeled mechanically valid, invalid, or inconclusive, with evidence and the next justified experiment.

## Practical validation example

For a request to compare the frozen strategy with controls, inspect the cash/equal-weight implementations and run:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f2_controls.py' -v
```

Confirm `test_cash_has_own_identity_and_constant_nav` and `test_equal_weight_has_own_artifacts_and_reconciled_book` pass. Explain why these checks support reproducible accounting but cannot reject the research null hypothesis. Do not manufacture a holdout from the four synthetic development cycles.
