# QTRE development instructions

Read the current branch/status, applicable instructions, `docs/especificacao-tecnica.md`,
`docs/roadmap-competencias.md`, and the relevant contracts before changing code.
The current engine demonstrates synthetic mechanics, not validated B3 performance.
Preserve unrelated local work; use a dedicated branch or isolated worktree.

## Research and correctness

- State hypothesis, baseline, inputs/outputs, assumptions, units, timing and expected
  hand-calculated quantities/cash/costs/NAV before changing financial behavior.
  Changing trading logic, strategy settings or calculations requires explicit scope approval.
- Preserve Decimal monetary precision, rounding rules and accounting identities.
  For floating-point analytics, justify precision, scale-aware tolerances and stability;
  reject non-finite inputs. Never replace Decimal accounting for speed alone.
- Enforce `available_at <= decision_at`, order-before-fill and next-open execution;
  preserve dated membership, delistings, revisions and missing-data states. Do not
  forward-fill execution data or turn `NAV_INCOMPLETO` into zero returns.
- Register hypotheses, every selection attempt, costs/slippage/impact assumptions,
  chronological splits and baseline before evaluation. Reserve the final test window;
  fit transforms only on training data and purge overlapping labels at split boundaries.
- Report sample size, uncertainty, multiple-testing/selection limits and dependence
  assumptions. Risk-adjusted metrics require explicit frequency/risk-free rate and
  complete aligned NAV. Synthetic fixtures cannot establish statistical significance.
- Record dataset version/hash/range, configuration, source/environment identity and
  seeds for stochastic components; use null with a reason for deterministic ones.

## Implementation and validation

- Keep modules small and typed at public boundaries. Python core stays standard-library
  only; project-local development dependencies are pinned in `requirements-dev.txt`.
  Preserve existing unittest compatibility; add pytest/property tests when useful.
- Use exact manual regression oracles, independent replay, leakage counterexamples,
  accounting invariants and bounded generated cases. Never weaken checks to pass CI.
- Run `make check` after substantive changes; `make core-test` needs no dev dependencies.
  Keep benchmarks serial; report hardware, repetitions and output equivalence.
- Review the diff, document limitations and report actual commands/results. No commit,
  push, merge or deployment is implied by a development request. Do not enable live
  trading, read brokerage credentials or commit private data/secrets.

## Codex workflow

Use `.agents/skills/quant-{research,backtest,risk,ml,performance}` for specialized
procedures. See `docs/codex/usage-guide.md` for setup/actions/experiments and
`docs/codex/architecture.md` for role handoffs and supported configuration.
Use at most three total concurrent agents (primary plus two); default to one worker.
Delegate only bounded independent work, assign disjoint files, and send evidence in
handoffs. Obtain independent review for substantive numerical/causal changes.


<!-- BEGIN CODEX QUANT OBSIDIAN v1 -->
## Contexto e registro no Obsidian

Este projeto participa da integração persistente com o vault `AI Quant`.
Leia `~/.codex/quant-obsidian.json` e a seção "Base de conhecimento Quant no Obsidian"
de `~/.codex/AGENTS.md`. Antes de implementar modelos, consulte a página deste projeto,
as pesquisas, decisões e experimentos pertinentes, além dos contratos do repositório.
Confirme tudo contra o estado atual do Git e do código.

Após tarefas relevantes, documente automaticamente objetivo/hipótese, implementação,
arquivos, metodologia, testes realmente executados/resultados, limitações e próximos
passos. Organize por projeto/modelo/experimento/decisão e use links internos do Obsidian.
Não invente evidências, duplique registros nem documente alterações triviais. Crie
notas novas sem sobrescrever notas pessoais ou excluir arquivos; releia para verificar.
Se o vault estiver pendente ou inacessível, informe a limitação e guarde um rascunho.
A integração não concede permissão para alterar lógica financeira, fazer commit/push
ou publicar dados. As demais instruções deste arquivo continuam em vigor.
<!-- END CODEX QUANT OBSIDIAN v1 -->
