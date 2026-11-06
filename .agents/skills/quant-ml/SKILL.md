---
name: quant-ml
description: Design or audit temporal features, labels, validation folds, tuning, and baseline comparisons for QTRE machine-learning research requests; does not imply a trained model already exists.
---

# Quant ML

Inspect `AGENTS.md`, the specification, roadmap, and current source before designing a study. QTRE's current F1/F2 validation is synthetic; supervised ranking is a future research direction, not an existing trained model or validated trading advantage.

## Workflow

1. Define the prediction target, decision time, label horizon and availability, instrument universe, economic objective, and allowable inputs. Separate predictive quality from profitability after costs. Do not implement or tune trading parameters without user authorization.
2. Build a feature/label provenance table with event time, publication time, revisions, lookback, transformation, and missingness. Lag inputs by actual availability; a row timestamp alone does not prove it was knowable. Preserve historical universe membership and delisted instruments.
3. Freeze chronological folds and an untouched final test before tuning. Purge training examples whose label information overlaps validation/test; use an embargo justified by lookbacks and label overlap, including the existing protocol requirements. Require training label availability before the fold's fitting cutoff. Never use random shuffled cross-validation for temporal trading evidence.
4. Fit imputation, scaling, encoding, feature selection, and any target-derived transforms only on each training fold, then apply frozen transforms forward. Avoid global normalization and full-sample feature selection. Cross-sectional transforms must use only the contemporaneously available eligible universe.
5. Compare simple predictive baselines and the fixed momentum/cash/equal-weight economic controls under comparable information and execution. Define predictive metrics, rank/tie handling, turnover, coverage, and net economic metrics before inspecting results.
6. Bound hyperparameter search by trials, time, memory, and seeds. Tune within development folds, record every trial and failure, and keep final-test access separate. Report dispersion and selection bias rather than only the best score. Stochastic algorithms require seeds plus software/hardware context; a seed alone may not guarantee bitwise determinism.
7. Assess regime sensitivity, leakage attacks, ablations, calibration where relevant, costs, and uncertainty with dependent observations. Without audited historical data and adequate holdout history, produce a protocol and mark performance evidence unavailable.

## Expected outputs

- A feature/label dictionary, temporal fold manifest, leakage checklist, and bounded search specification.
- A complete trial record with seeds, configurations, dataset/code identity, fold metrics, baselines, and exclusions.
- A model/research report stating what exists, what was tested, and what remains hypothetical.

## Practical validation example

Manual protocol example, not an implemented ML pipeline: a training row observed February 28 has a forward label available March 15; validation starts March 1. A March 1 fit cannot use that label even though the row's feature date precedes the validation period. Purge that row or move the fitting cutoff consistently; do not relabel it as historical knowledge. Likewise, changing March validation values must not change a scaler fit only on January-February training features.

Run QTRE's existing causal-data check as a prerequisite, not as proof of ML validation:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f2_audit.py' -v
```

Expected: future information in decision inputs is rejected even if artifact hashes are internally consistent. A separate ML fold/transform implementation and tests remain necessary before any trained-model claim.
