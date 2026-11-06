# Quant development environment audit

Audit date: 2026-11-06. Baseline commit: `e86375ffec978ab1f9edf8cfe9cabc7d0fc8da0f`.
Work is isolated on dedicated branch `codex/quant-research-environment`.

## Findings

| Area | Finding before this task | Assessment |
|---|---|---|
| Architecture | Python >=3.10, setuptools, `src/qtre`; standard-library core with Decimal accounting | Preserve engine and financial formulas |
| Data | Frozen point-in-time snapshots, versioned synthetic calendars, provenance and availability checks | Synthetic mechanics; no verified B3 dataset |
| Research | Momentum 12–2, monthly backtest, cash/equal-weight controls, cost sensitivity, independent artifact replay and causal audit | Functional F1/F2 synthetic research; roadmap lags some implemented controls |
| Components | `data`, `calendar`, `universe`, `signals`, `backtest`, `reporting`, `validation` | Supervised ML remains planned; no trained model or live trading |
| Dependencies | Optional `yfinance>=0.2`; no runtime core dependencies or development lock | Keep optional network probe outside offline validation |
| Tests | 123 unittest tests passed in 20.910 seconds on baseline working tree | Includes local uncommitted summary tests; strong regression and adversarial coverage |
| CI | No `.github` workflows found | Add bounded offline tests, lint and format gates |
| Codex | CLI 0.155.1; no repository AGENTS.md, `.agents` or `.codex` configuration; no applicable ancestor AGENTS.md found | Verify role/action syntax against installed runtime before configuring |
| Experiment tracking | Existing run manifests, canonical SHA-256 artifact hashes, deterministic replay/audit; benchmark script | Extend provenance and lifecycle around existing outputs; no MLflow server needed |
| Documentation | Specification, snapshot/artifact contracts, research protocol, roadmap, reviews | Preserve all existing research documents; add separate development docs |
| Hardware | Fedora Linux 44, Python 3.14.7, Ryzen 5 7535HS (12 logical CPUs), 5.46 GiB RAM | About 792 MiB available and 3.19 GiB swap used at inspection: serial tests/builds, at most three agents |
| Sandbox | Workspace-write; `.git`, `.agents`, `.codex` protected; network restricted | Local branch creation needed targeted approval-tool escalation; succeeded. No system-wide modification |

## Existing work preserved

Before task: modified `README.md`, `docs/roadmap-competencias.md`; untracked
`docs/resumo-f2-v1.md`, `docs/status-projeto.md`, `src/qtre/validation/summary.py`,
`tests/test_f2_summary.py`. Content hashes captured before edits for final preservation
check. These files are outside the implementation scope.

## Available capabilities

The session provides filesystem/terminal tools, browser and web access, Codex app
project/worktree tools, collaboration tools, official skill creation guidance, and
optional connected-service tools. Relevant existing skills include skill creation,
code review, security review and document tooling. Their presence is not evidence
that a remote account is authorized. No external service is required for this
local offline workflow. Installed Codex compatibility evidence and exact roles are
recorded in `architecture.md` after verification. No integration will be installed
or authorized by this task.

## Prioritized implementation plan

1. Preserve baseline and isolate branch; record baseline tests and constraints.
2. Add concise root instructions, five discoverable quantitative skills and supported
   specialist roles with explicit handoffs and independent review boundaries.
3. Add a pinned project-local development environment, pytest compatibility,
   bounded property tests, scoped lint/format gates and GitHub Actions.
4. Add a standard-library experiment wrapper recording input/configuration,
   source hashes, environment, status, metrics and immutable engine artifacts.
   Verify duplicate rejection, failure tracking, tamper detection and reproduction.
5. Add supported desktop setup/actions, operating guide and architecture docs.
6. Run static config checks, the full suite, a minimal experiment and reproduction;
   review independently and record exact results and remaining limitations.

## Risks and decisions

- Hash integrity does not prove causal/economic validity; retain independent replay
  and causal audit. Incomplete NAV must stay incomplete and suppress return claims.
- Four synthetic cycles cannot support statistical inference or performance claims.
  No new risk formulas, strategy parameters, ML training or simulation are authorized.
- Preserve original unittest runner; pytest is a development dependency only.
- Avoid formatting existing financial code. Apply formatting to new infrastructure;
  use a narrowly scoped fatal-error lint gate for legacy source.
- Use local JSON experiment envelopes and existing engine artifacts instead of
  MLflow: no service/database, credentials, network fetch or large dependency stack.
- Source hashes identify dirty/untracked source; exact reruns still require retaining
  the matching source checkout. Never archive secrets or arbitrary local files.
- Hosted CI execution requires later publication. Local validation cannot claim a
  successful GitHub-hosted run or a refreshed desktop skill/agent picker.

## Post-implementation verification

The installed CLI loaded four roles and discovered all five repository skills. The
current desktop task also refreshed its skill catalog with those entries. Desktop
package 26.917.71314 schema compatibility was inspected locally. Final full pytest
validation passed 140 cases; the original unittest suite still passed 123 cases.
Two experiment attempts produced identical verified engine artifacts. See
[implementation report](implementation-report.md) for exact evidence, original-file
preservation, dependency additions and remaining hosted/UI verification limits.
