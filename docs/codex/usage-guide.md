# Using the Quant development environment

## First setup

Open this repository in Codex. Read `AGENTS.md` and the relevant research contracts.
From the repository root, run:

```sh
make setup
make check
make core-test
make codex-check
```

Setup creates only `.venv`, installs the pinned `requirements-dev.txt`, and installs
the package editable without build isolation or dependency resolution. First setup
requires package-index access; no global package or Codex settings are changed.
Python >=3.10 and POSIX make are required. Fedora Python 3.14.7 was locally tested;
Python 3.10 is included in CI but was not installed locally. On Windows use WSL for
these Makefile commands and the POSIX Codex probe. Commands run serially with common
numerical-library thread counts capped at one.

`make core-test` runs the existing standard-library suite without development
dependencies. `make check` runs new-tool lint/format checks, fatal-error lint for
legacy source, structural configuration validation and the full pytest suite.
`make codex-check` requires installed Codex and checks actual role/skill discovery
without a model call, external integrations, or changes to global Codex trust.

## Desktop actions and roles

The project environment is `.codex/environments/environment.toml`. It supplies:

| Action | Command | Expected behavior |
|---|---|---|
| Validate environment | `make check` | Offline checks and full suite |
| Core offline tests | `make core-test` | Original unittest suite |
| Synthetic experiment | `make experiment` | New unique directory under ignored `.runs/` |
| Bounded benchmark | `make benchmark` | Three repetitions plus warmup, output hash and timings |

The setup hook runs `make setup` in new managed worktrees. These commands were
validated directly; desktop toolbar clicks/worktree auto-setup were not exercised.
For an existing task, reload/reopen project context if role/action entries are not
shown. Skills were both runtime-discovered and observed in this task's skill catalog.

Invoke a skill explicitly, for example `$quant-backtest`, or describe the matching
research task. The five skills may be selected automatically from their descriptions.
Ask the coordinator for a specialist by configured role when useful:

- `quant_research`: formulate a study and its acceptance criteria.
- `quant_developer`: implement the approved bounded change.
- `statistical_validation`: independently challenge temporal/statistical validity.
- `risk_code_review`: independently review accounting, risk conventions and code.

Give each worker exact file ownership and a bounded question. Return raw evidence,
commands, results and uncertainty. Use no more than two child agents concurrently;
run tests/builds serially on this machine. Independent reviewers do not edit the
submitted change. Agent role names are configuration entries, not callable shell
commands, and their read-only restrictions are instructions rather than separate
permission sandboxes.

## Safe worktree workflow

This task used dedicated branch `codex/quant-research-environment`, preserving the
six pre-existing dirty files. The environment was committed locally in separate
commits. A new Git worktree contains committed files only; it will not automatically
inherit unrelated local edits. Transfer only required local files with provenance.
Use the Codex app's managed worktree workflow for future isolated tasks; leave
experimental CLI worktree feature flags alone. Each worktree gets its own `.venv`
and `.runs`; do not run competing writes to the same experiment directory.

## Run and reproduce an experiment

The minimal wrapper uses the existing single-formation F1 fixture and unchanged
strategy defaults. It does not add monthly parameter search or a new risk metric.
After setup:

```sh
PYTHONPATH=src:. .venv/bin/python tools/qtre_experiment.py run --output .runs/example-001
PYTHONPATH=src:. .venv/bin/python tools/qtre_experiment.py reproduce .runs/example-001 --output .runs/example-001-copy
```

Choose new output paths each time. `make experiment` generates a unique path for you.
The returned JSON points to `experiment.json` and its sibling `engine/` artifacts.
The fixed example's existing first-formation contract yields final NAV `100085.01`
BRL and one incomplete intermediate NAV mark; the successful causal audit validates
mechanics and the missing-data policy. Do not infer a full-period return or market
performance from that final value.

For another authorized synthetic F1 input, pass `--snapshot PATH` and
`--decision-at ISO_TIMESTAMP_WITH_TIMEZONE`. Equivalent timezone representations
normalize to UTC. Default configuration and seed=null are deliberate: no strategy
parameter overrides or stochastic calculation are introduced.

Reproduction verifies original artifact hashes, independent replay, causal audit,
dataset/metric metadata, current source hashes and exact Python runtime; it then
requires identical newly produced engine artifacts and metrics. Attempt IDs and
timestamps will differ. Keep the original source checkout: hashes identify code but
do not restore it. Source edits—including development-tool edits—require returning
to the recorded version or creating a new experiment instead of relabeling the old
one. A dirty Git flag means HEAD alone does not identify the full experiment source.

Failed runs preserve their exception type/message and status, and caught interruptions
preserve INTERRUPTED. Hard kills can leave RUNNING; treat these as unfinished and use
a new directory. Nonzero command status is failure. Existing output directories are
never silently overwritten. Do not manually fix hashes or completion status to bypass
an audit. `.runs` is ignored; do not publish private input datasets or sensitive errors.

## Research and performance workflow

Use the specialized skills for procedural details. Before financial code changes,
record the hypothesis, baseline, units, temporal cutoffs and hand-calculated example,
and obtain the necessary change scope. Current synthetic history does not support
out-of-sample performance inference or trained-model
validation. Preserve incomplete NAV and all attempts, including negative results.

For profiling, use the existing benchmark and the quant-performance skill. Compare
output hashes first, then warmed repeated timings on the same hardware. No speed
improvement was implemented by this environment task. Keep generated reports in
ignored `.runs` or temporary directories.

## CI and integrations

GitHub Actions configuration validates Python 3.10 and 3.14 serially, including setup,
checks, the original suite, and experiment reproduction. Local structural YAML/TOML
validation and equivalent commands passed. A hosted run is pending publication;
there is no deployment/CD step. Do not push or merge without explicit authorization.

No MCP installation is necessary. Existing GitHub tooling can later inspect remote
CI and review evidence; official documentation search can clarify future API changes.
Neither capability requires adding a new server for current offline tests. External
data providers, MLflow hosting, brokers and new authorizations remain outside scope.
