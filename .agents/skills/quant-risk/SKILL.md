---
name: quant-risk
description: Specify or review QTRE portfolio risk, drawdown, exposure, stress scenarios, and tail-risk calculations when a research request needs risk analysis or risk validation.
---

# Quant Risk

Read the current risk-related implementation and `docs/protocolo-pesquisa-f2-v1.md`. The current synthetic series is insufficient for inferential tail-risk or annualized estimates. This skill provides analysis procedures; it does not imply a VaR/ES engine is implemented.

## Workflow

1. Establish NAV completeness, cash flows, return convention, observation spacing, valuation currency, and horizon. Reject nonfinite values and explain gaps; never impute a missing mark as zero return.
2. Define volatility estimator and degrees of freedom. Annualize only with an explicit sampling-frequency and dependence assumption. Define drawdown as NAV/running peak minus one and state whether the reported maximum is a positive loss magnitude or a negative return; define duration/recovery and units.
3. Reconcile gross/net exposure, cash, sector/name concentration, and leverage to portfolio holdings and NAV. Record currency and denominator; undefined ratios for zero/incomplete NAV are unavailable rather than zero.
4. For VaR/Expected Shortfall, define loss as positive, confidence level, horizon, units, sample window, quantile convention, and tail-mass weighting. Historical, parametric, and simulation estimators have different assumptions. Avoid treating volatility or normality as proof about tails; report effective tail observations and uncertainty.
5. Specify deterministic stress scenarios (price gaps, correlated falls, liquidity/cost shocks, missing marks) and assumptions. Keep scenario P&L separate from probabilistic VaR. Add joint stresses when dependence or concentration matters, and report when market impact or nonlinear exposures are unmodeled.
6. Validate formulas with a hand-worked example, scale/sign checks, and extreme/empty/constant cases before proposing implementation. Financial calculation changes still require explicit authorization. Review tail sensitivity and estimator failure modes, not just a passing numerical test.

## Expected outputs

- A risk specification with formulas, units, horizon, data adequacy, conventions, and missing-data policy.
- Reconciled exposure/stress tables and numerical checks, with unsupported metrics explicitly unavailable.
- Interpretation distinguishing measured historical risk, model assumptions, and hypothetical stress losses.

## Practical validation example

Manual analysis example, not a repository risk implementation: NAV `[100, 120, 90]` has drawdowns `[0, 0, -0.25]`, so maximum drawdown loss magnitude is 25%. Scaling every NAV by ten leaves this ratio unchanged.

For five equally weighted losses `[0, 1, 2, 3, 4]` BRL, 80% empirical VaR using the generalized inverse empirical CDF is 3 BRL. ES defined as the mean of the worst 20% probability mass is 4 BRL. Averaging all losses greater than or equal to VaR would incorrectly return 3.5 BRL under this ES convention. These five values illustrate arithmetic only, not reliable tail estimation.

The existing missing-mark guard can be exercised with:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f1_backtest.py' -v
```

Confirm `test_suspension_split_dividend_and_missing_mark` passes before analyzing NAV-based risk.
