# Quant research development architecture

## Scope and layers

The financial engine is unchanged. Development infrastructure wraps its existing
synthetic contracts. A supervised ML study is planned; no model has been trained.

```text
AGENTS.md -> specialized .agents/skills/*/SKILL.md
          -> .codex/config.toml -> four role instruction files
          -> .codex/environments/environment.toml -> Makefile actions

make check -> pinned local tools -> lint + format + config + pytest
                                   existing unittest tests + bounded properties

experiment wrapper -> frozen snapshot -> existing run_f1
                   -> existing write_f1_run -> independent replay / causal audit
                   -> experiment.json + hashed engine artifacts
```

The core remains standard-library Python >=3.10 with Decimal accounting. New
utilities live in `tools/`, outside the distributed `qtre` package. This avoids
changing engine code hashes or exposing development tools as financial APIs.
The experiment wrapper uses existing canonical JSON reading, artifact persistence,
backtest and audit APIs; the underscore-prefixed JSON reader is an explicit internal
coupling covered by tests, not a new public financial interface.

## Instructions and skills

Root `AGENTS.md` supplies the common correctness/scope rules and routes detail to:

| Skill | Responsibility | Existing implementation boundary |
|---|---|---|
| quant-research | Hypothesis, mathematical assumptions, units, baselines, trial design and interpretation | Synthetic protocol and controls |
| quant-backtest | Availability, fills, accounting, costs, attribution and holdout integrity | F1/F2 replay, audit and cost tests |
| quant-risk | Volatility/drawdown, exposure, VaR/ES conventions, stress and tails | Procedures/manual examples; no new risk engine |
| quant-ml | Features/labels, temporal folds, transforms, leakage, tuning, baseline comparison | Future study design; no trained model |
| quant-performance | Profile first, output equivalence, memory and vectorization | Existing three-cycle Python benchmark |

Each skill has YAML name/description, workflow, outputs, a practical example and
UI metadata. The official skill creator's validator passed all five. The installed
runtime discovered all five, and this desktop task's available-skill catalog refreshed
to include them during implementation.

## Agent responsibilities and handoffs

| Configured role | Inputs and outputs | Tools and boundaries |
|---|---|---|
| `quant_research` | Question/contracts -> preregistration, manual expected values, evidence requirements | Read/search, small offline calculations; research code changes require approved scope |
| `quant_developer` | Approved protocol + assigned files -> diff, tests, artifacts, limitations | File edits and bounded tests only in assigned scope; cannot independently approve own work |
| `statistical_validation` | Raw protocol, diff and artifacts -> PASS/FAIL/INCONCLUSIVE with evidence | Read-only instruction boundary; temporary tests; challenges leakage, dependence and selection |
| `risk_code_review` | Diff, contracts and reconciliations -> actionable findings with severity | Read-only instruction boundary; temporary tests; accounting, incomplete NAV, costs and risk conventions |

The primary coordinator assigns disjoint files, merges findings and resolves scope.
Handoffs include objective, approved boundaries, exact files, assumptions, input/output
identities, commands/results, unresolved questions and the next acceptance check.
Reviewers receive raw evidence and a neutral question. They do not receive an expected
verdict. A reviewer returns findings for the owner to repair; the coordinator verifies
repairs before reporting completion. Review is independent of authoring, not a guarantee
of infallibility.

`max_concurrent_threads_per_session = 2` limits child agents: primary plus two children
is three total. Default to one worker, no recursive spawning and serial local builds.
The four roles are available choices, not four simultaneously running processes.
Role permissions and MCP connections inherit the parent. Read-only roles are explicit
behavioral instructions, not a separate enforced sandbox/tool allowlist. Model selection
and reasoning settings inherit user preferences; no model override is pinned.

## Installed Codex compatibility evidence

Verified on 2026-11-06: CLI `0.155.1`, desktop package `26.917.71314` (installed
`/usr/lib/chatgpt/resources/app.asar`). The app's bundled local-environment parser
accepts `version`, `name`, `[setup].script` and `[[actions]]` with name/icon/command.
The committed environment uses only those verified fields.

Actual CLI app-server JSON-RPC `config/read` loaded all four project roles and resolved
their `config_file` paths; `skills/list` discovered all five skills without errors.
`make codex-check` reproduces discovery using a temporary Codex home and temporary
project trust, with plugins/apps disabled and no copied credentials/model turn.
It does not change global settings. `make config-check` is the portable offline
structural check; the live CLI probe requires POSIX and installed compatible Codex.

Custom-role spawning and desktop toolbar clicks remain unverified. A managed
worktree was created during the 06/11 reconciliation, but automatic setup was
not exercised. The collaboration
review used session agents, independently of the four newly configured role entries.
Official reference context: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[skills](https://learn.chatgpt.com/docs/build-skills), and
[local environments](https://learn.chatgpt.com/docs/environments/local-environment).
Installed-runtime evidence takes precedence over assumptions about newer documentation.

## Validation and dependencies

`requirements-dev.txt` pins direct and transitive development dependencies. Pytest runs
existing unittest cases without rewriting them; Hypothesis adds two bounded property
tests (40 deterministic examples each). The exhaustive Decimal affordability oracle
is independent of the engine's binary search; temporal cases probe future-cache
contamination and monotone availability. Existing manual numerical regression,
cost, leakage and independent replay tests remain authoritative.

Ruff applies normal correctness lint and formatting only to new `tools/` and
`tests/dev/`. A fatal-error subset checks all existing Python files, avoiding an
unrelated financial-source reformat. TOML/YAML and skill/role/action consistency are
checked offline. GitHub Actions runs Python 3.10 and 3.14 serially, with read-only
repository permissions, 15-minute job limits, canceled superseded runs, and no deploy.
Hosted runner/action images are not immutable; package versions are pinned but wheel
hashes and a container image are not. This is version reproducibility, not a hermetic
supply-chain build. The optional Yahoo dependency remains outside this environment.

## Experiment storage contract

Each caller-selected new directory contains an atomically replaced `experiment.json`
and an `engine/` directory. Existing directories are rejected. The engine persists
its snapshot, manifest, orders, states, fills, ledger, NAV and audit. The wrapper records:

- UUID attempt identifier, RUNNING/COMPLETED/FAILED/INTERRUPTED status and UTC timestamps;
- complete existing strategy configuration/model ID and engine run ID;
- snapshot content hash, schema, calendar, inclusive calendar coverage and as-of time;
- canonical UTC decision instant, seed null plus deterministic explanation;
- Git HEAD and dirty flag, hashes of all engine/tool source plus dependency/project files;
- Python version/implementation/platform and installed direct development tool versions;
- artifact hashes, audit/count metrics and existing final cash/NAV values.

No new return/risk calculation is introduced. Incomplete NAV count remains visible;
final NAV alone is not a valid complete-period return. Attempt UUID/time/Git metadata
can differ while engine artifact bytes remain identical. Reproduction validates saved
metadata against artifacts, replays/audits the original, requires matching source hashes
and exact Python version/implementation, reruns the saved snapshot with unchanged F1
defaults, then requires identical artifact hashes and metrics.

The wrapper intentionally supports only the existing one-formation F1 experiment.
Monthly controls/cost sweeps retain their existing APIs; this is not a generic ML
tracker. Source is identified but not archived: retain the matching dirty checkout
or commit the approved files later to reproduce. Git metadata records a local claim,
not an authenticity signature. Versioned source/artifacts must be preserved separately.
Caught failures/interruptions retain status; hard process termination/power loss can
leave RUNNING, which must be treated as unfinished. A failure before initial metadata
can be written (permissions/disk full) cannot guarantee a record. No database/server,
credential collection, automatic data fetching or external integrations are required.
