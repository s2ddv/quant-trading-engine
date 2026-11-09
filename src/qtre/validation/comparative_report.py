"""Read and compare nine persisted synthetic F2 cost runs."""

import argparse
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

from qtre.reporting import FILES, ReplayError, _json, _load_json
from qtre.validation.cost_sensitivity import SCENARIOS, STRATEGIES, _report_run, compare_pair


class InvalidSource(ValueError):
    """A persisted comparison source fails the v1 contract."""


_COST_KEYS = ("half_spread_bps", "slippage_bps", "fees_bps")
_COMMON_WINDOWS = ("decision_at", "formation_session", "execution_sessions", "bridge_sessions")


def _read_json(path: Path) -> tuple[dict, str]:
    if not path.is_file() or path.is_symlink():
        raise InvalidSource(f"{path}: missing, unreadable or linked file")
    raw = path.read_bytes()
    value = _load_json(raw, str(path))
    if not isinstance(value, dict):
        raise InvalidSource(f"{path}: expected JSON object")
    return value, sha256(raw).hexdigest()


def _require(condition: bool, path: Path, reason: str) -> None:
    if not condition:
        raise InvalidSource(f"{path}: {reason}")


def _identity(run: dict) -> dict:
    return {
        "snapshot_hash": run["snapshot_hash"],
        "calendar_id": run["calendar_id"],
        "model_id": run["model_id"],
        "code_hash": run["code_hash"],
        "decision_ats": [window["decision_at"] for window in run["decision_windows"]],
        "config": run["config"],
    }


def _run_cell(root: Path, strategy: str, scenario: str, sensitivity: dict) -> tuple[dict, dict]:
    path = root / f"{strategy}-{scenario}"
    _require(path.is_dir() and not path.is_symlink(), path, "missing or linked run directory")
    manifest, manifest_hash = _read_json(path / "manifest.json")
    audit, _ = _read_json(path / "audit.json")
    _require(set(manifest["files"]) == set(FILES), path / "manifest.json",
             "artifact file set mismatch")
    for name in FILES:
        artifact = path / name
        _require(artifact.is_file() and not artifact.is_symlink(), artifact,
                 "missing, unreadable or linked artifact")
    run = manifest["run"]
    _require(run["synthetic"] is True, path, "run is not synthetic")
    _require(audit["status"] == "VALID", path, "persisted audit is not VALID")
    _require(audit["run_id"] == run["run_id"] == sensitivity["run_id"], path, "run_id mismatch")
    _require(audit["manifest_sha256"] == manifest_hash, path, "audit manifest hash mismatch")
    _require(audit["artifact_hashes"] == manifest["files"], path, "audit artifact hashes mismatch")
    _require(run.get("control_id") == (None if strategy == "momentum" else strategy),
             path, "strategy control mismatch")
    expected_costs = dict(zip(_COST_KEYS, next(row[1:] for row in SCENARIOS if row[0] == scenario)))
    try:
        costs_match = all(Decimal(run["config"][key]) == expected_costs[key] for key in _COST_KEYS)
    except InvalidOperation as exc:
        raise InvalidSource(f"{path}: invalid scenario cost") from exc
    _require(costs_match, path, "scenario costs mismatch")
    # audit_f1_run writes an audit only when absent; its existing bytes are checked above.
    summary = _report_run(path)
    _require(summary["run_id"] == run["run_id"], path, "replay identity mismatch")
    observed = _load_json(_json(summary), str(path / "sensitivity.json"))
    _require(observed == sensitivity, path, "sensitivity run mismatch")
    bps = summary["costs_bps"]["total"]
    cell = {
        "source_path": path.name,
        "run_id": run["run_id"],
        "manifest_sha256": manifest_hash,
        "audit_status": "VALID",
        "identity": _identity(run),
        "decisions": summary["decisions"], "sessions": summary["sessions"],
        "orders": summary["orders"], "fills": summary["fills"],
        "costs_brl": summary["costs_brl"],
        "costs_bps": {"total": bps, "status": "AVAILABLE" if bps is not None else "UNAVAILABLE_NO_NOTIONAL"},
        "final_cash_brl": summary["final_cash_brl"],
        "final_receivable_brl": summary["final_receivable_brl"],
        "final_positions_value_brl": summary["final_positions_value_brl"],
        "final_nav_brl": summary["final_nav_brl"],
        "incomplete_sessions": summary["incomplete_sessions"],
        "cumulative_return": summary["complete_series_return"],
        "return_status": summary["return_status"],
    }
    return cell, run


def _validate_identities(root: Path, manifests: dict) -> None:
    seen = set()
    reference = manifests["momentum"]["zero"]
    for strategy in STRATEGIES:
        first = manifests[strategy]["zero"]
        for scenario, *_ in SCENARIOS:
            run = manifests[strategy][scenario]
            path = root / f"{strategy}-{scenario}"
            _require(run["run_id"] not in seen, path, "duplicate run_id")
            seen.add(run["run_id"])
            for key in ("snapshot_hash", "calendar_id", "code_hash", "decision_at", "formation_session"):
                _require(run[key] == reference[key], path, f"common {key} mismatch")
            _require([tuple(w[key] for key in _COMMON_WINDOWS) for w in run["decision_windows"]]
                     == [tuple(w[key] for key in _COMMON_WINDOWS) for w in reference["decision_windows"]],
                     path, "common decision windows mismatch")
            _require(run["model_id"] == first["model_id"], path, "model mismatch within strategy")
            _require(run["decision_windows"] == first["decision_windows"], path,
                     "decision windows mismatch within strategy")
            _require({key: value for key, value in run["config"].items() if key not in _COST_KEYS}
                     == {key: value for key, value in reference["config"].items() if key not in _COST_KEYS},
                     path, "non-cost config mismatch")
            _require(all(run[key] == first[key] for key in
                         ("settlement", "monetary_rounding", "decimal_precision")),
                     path, "execution assumptions mismatch")
            _require(all(run[key] == reference[key] for key in
                         ("settlement", "monetary_rounding", "decimal_precision")),
                     path, "common execution assumptions mismatch")


def read_comparative_report(directory: str | Path) -> dict:
    """Return the deterministic v1 report without changing persisted artifacts."""
    root = Path(directory)
    _require(root.is_dir(), root, "missing source directory")
    sensitivity, sensitivity_hash = _read_json(root / "sensitivity.json")
    _require(sensitivity.get("report_schema_version") == 1 and sensitivity.get("synthetic") is True,
             root, "unsupported sensitivity source")
    expected = {f"{strategy}-{scenario}" for strategy in STRATEGIES for scenario, *_ in SCENARIOS}
    _require({child.name for child in root.iterdir() if child.is_dir()} == expected,
             root, "run directory set mismatch")
    _require(set(sensitivity["runs"]) == set(STRATEGIES), root, "strategy set mismatch")
    _require(sensitivity.get("scenarios_bps") == {
        name: {"half_spread": spread, "slippage": slippage, "fees": fees}
        for name, spread, slippage, fees in SCENARIOS}, root, "scenario definition mismatch")
    runs, manifests = {}, {}
    for strategy in STRATEGIES:
        _require(set(sensitivity["runs"][strategy]) == {row[0] for row in SCENARIOS},
                 root, f"{strategy} scenario set mismatch")
        runs[strategy], manifests[strategy] = {}, {}
        for scenario, *_ in SCENARIOS:
            try:
                cell, run = _run_cell(root, strategy, scenario, sensitivity["runs"][strategy][scenario])
            except (OSError, ReplayError, ValueError, KeyError, TypeError, IndexError,
                    InvalidOperation) as exc:
                raise InvalidSource(f"{root / f'{strategy}-{scenario}'}: {exc}") from exc
            runs[strategy][scenario], manifests[strategy][scenario] = cell, run
    _validate_identities(root, manifests)
    comparisons = {}
    for strategy in STRATEGIES:
        comparisons[strategy] = {}
        for earlier, later in (("zero", "base"), ("base", "high")):
            pair = f"{earlier}_to_{later}"
            path = root / f"{strategy}-{earlier}"
            result = compare_pair(path, root / f"{strategy}-{later}", raise_on_fail=False)
            prior = sensitivity["comparisons"][strategy][pair]
            _require(_load_json(_json(result), str(path)) == prior, path,
                     f"sensitivity comparison {pair} mismatch")
            reason = None
            if result["monotonicity"] == "NOT_COMPARABLE_EXECUTION_CHANGED":
                reason = "fills_and_nav_schedule_differ" if not result["fills_identical"] and not result["nav_schedule_identical"] else \
                         "fills_differ" if not result["fills_identical"] else "nav_schedule_differs"
            comparisons[strategy][pair] = {
                "earlier_run_id": runs[strategy][earlier]["run_id"],
                "later_run_id": runs[strategy][later]["run_id"],
                "fills_identical": result["fills_identical"],
                "nav_schedule_identical": result["nav_schedule_identical"],
                "monotonicity": result["monotonicity"], "reason": reason,
                "nav_points_compared": result.get("nav_points_compared"),
            }
    return {"report_schema_version": 1,
            "source": {"path": str(root), "sensitivity_sha256": sensitivity_hash, "synthetic": True},
            "runs": runs, "comparisons": comparisons}


def report_json(report: dict) -> bytes:
    """Serialize with stable keys and exact Decimal strings."""
    return _json(report) + b"\n"


def report_table(report: dict) -> str:
    """Render a compact human readable table from the validated report."""
    columns = ("strategy", "scenario", "decisions", "sessions", "orders", "fills",
               "spread BRL", "slippage BRL", "fees BRL", "total BRL",
               "cash BRL", "receivable BRL", "positions BRL", "NAV BRL", "return status")
    rows = [columns]
    for strategy in STRATEGIES:
        for scenario, *_ in SCENARIOS:
            cell = report["runs"][strategy][scenario]
            rows.append((strategy, scenario, str(cell["decisions"]), str(cell["sessions"]),
                         str(cell["orders"]), str(cell["fills"]),
                         *(str(cell["costs_brl"][key]) for key in
                           ("spread_cost", "slippage_cost", "fees", "total")),
                         str(cell["final_cash_brl"]), str(cell["final_receivable_brl"]),
                         str(cell["final_positions_value_brl"]), str(cell["final_nav_brl"]),
                         cell["return_status"]))
    widths = [max(len(row[index]) for row in rows) for index in range(len(columns))]
    lines = ["  ".join(value.ljust(widths[index]) for index, value in enumerate(row)).rstrip()
             for row in rows]
    lines.insert(1, "  ".join("-" * width for width in widths))
    lines.append("")
    for strategy in STRATEGIES:
        for pair, comparison in report["comparisons"][strategy].items():
            lines.append(f"{strategy} {pair}: {comparison['monotonicity']}"
                         + (f" ({comparison['reason']})" if comparison["reason"] else ""))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a persisted F2 comparative report")
    parser.add_argument("directory", help="directory containing sensitivity.json and nine runs")
    parser.add_argument("--format", choices=("json", "table"), default="table")
    args = parser.parse_args(argv)
    try:
        report = read_comparative_report(args.directory)
    except (ValueError, OSError, KeyError, TypeError, IndexError, InvalidOperation) as exc:
        parser.exit(2, f"INVALID_SOURCE: {exc}\n")
    if args.format == "json":
        import sys
        sys.stdout.buffer.write(report_json(report))
    else:
        print(report_table(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
