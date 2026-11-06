"""Offline experiment lifecycle around the unchanged synthetic F1 engine."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import subprocess
import uuid

from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot
from qtre.reporting import _load_json, replay_f1, write_f1_run
from qtre.validation import audit_f1_run

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "examples/synthetic_f1_v1.json"
DEFAULT_DECISION = "2025-01-31T20:07:00+00:00"
ARTIFACTS = (
    "snapshot.json",
    "manifest.json",
    "orders.jsonl",
    "order_states.jsonl",
    "fills.jsonl",
    "ledger.jsonl",
    "nav.jsonl",
    "audit.json",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def source_identity() -> dict[str, str]:
    """Hash only known code/config paths; never archive arbitrary local files."""
    paths = [*ROOT.glob("src/qtre/**/*.py"), *ROOT.glob("tools/*.py")]
    paths += [ROOT / "pyproject.toml", ROOT / "requirements-dev.txt"]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


def environment() -> dict:
    packages = {}
    for name in ("pytest", "hypothesis", "ruff", "PyYAML", "tomli", "setuptools", "wheel"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "development_packages": packages,
    }


def git_identity() -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=normal")),
    }


def save_record(directory: Path, record: dict) -> None:
    temporary = directory / "experiment.json.tmp"
    temporary.write_text(json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n")
    temporary.replace(directory / "experiment.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("decision must have an explicit timezone")
    return parsed.astimezone(timezone.utc)


def dataset_metadata(snapshot) -> dict:
    sessions = [row["session"] for row in snapshot.payload["calendar"]["sessions"]]
    return {
        "content_sha256": snapshot.content_hash,
        "calendar_id": snapshot.calendar_id,
        "schema_version": snapshot.payload["schema_version"],
        "start_session": min(sessions),
        "end_session": max(sessions),
        "as_of": snapshot.as_of.isoformat(),
    }


def metrics_from(result: dict, audit: dict) -> dict:
    """Expose existing engine values/counts; add no new financial calculations."""
    return {
        "audit_status": audit["status"],
        **audit.get("counts", {}),
        "last_cash_brl": str(result["nav"][-1]["cash_brl"]),
        "last_nav_brl": (
            str(result["nav"][-1]["nav_brl"]) if result["nav"][-1]["nav_brl"] is not None else None
        ),
        "performance_inference": "NOT_APPLICABLE: synthetic mechanics only",
    }


def run_experiment(snapshot_path: Path, decision_at: str, output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1,
        "experiment_id": str(uuid.uuid4()),
        "status": "RUNNING",
        "started_at": utc_now(),
        "seed": None,
        "seed_reason": "F1 execution is deterministic; no random generator is used",
        "request": {"decision_at": decision_at, "snapshot_name": Path(snapshot_path).name},
    }
    save_record(output, record)
    try:
        record.update(source_files=source_identity(), git=git_identity(), environment=environment())
        snapshot = load_snapshot(snapshot_path)
        decision = instant(decision_at)
        record["request"]["decision_at"] = decision.isoformat()
        record["dataset"] = dataset_metadata(snapshot)
        result = run_f1(snapshot, decision_at=decision)
        directory = write_f1_run(snapshot, result, output / "engine")
        record["engine_run"] = result["manifest"]
        audit = audit_f1_run(directory)
        record["artifacts"] = {name: digest(directory / name) for name in ARTIFACTS}
        if audit["status"] != "VALID":
            raise ValueError("causal audit rejected the experiment")
        record["metrics"] = metrics_from(result, audit)
        record["status"] = "COMPLETED"
    except BaseException as exc:
        record["status"] = (
            "INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "FAILED"
        )
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        record["finished_at"] = utc_now()
        save_record(output, record)
    return record


def read_verified(directory: Path) -> dict:
    directory = Path(directory)
    record = _load_json((directory / "experiment.json").read_bytes(), "experiment.json")
    if record.get("schema_version") != 1 or record.get("status") != "COMPLETED":
        raise ValueError("expected a completed schema-1 experiment")
    if set(record["artifacts"]) != set(ARTIFACTS):
        raise ValueError("unexpected artifact set")
    for name, expected in record["artifacts"].items():
        if digest(directory / "engine" / name) != expected:
            raise ValueError(f"artifact hash mismatch: {name}")
    envelope = _load_json((directory / "engine/manifest.json").read_bytes(), "manifest")
    if record["engine_run"] != envelope["run"]:
        raise ValueError("experiment configuration differs from engine manifest")
    if record["dataset"]["content_sha256"] != envelope["run"]["snapshot_hash"]:
        raise ValueError("dataset identity differs from engine manifest")
    if instant(record["request"]["decision_at"]) != instant(envelope["run"]["decision_at"]):
        raise ValueError("decision differs from engine manifest")
    replay_f1(directory / "engine")
    audit = audit_f1_run(directory / "engine")
    if audit["status"] != "VALID":
        raise ValueError("causal audit rejected saved experiment")
    snapshot = load_snapshot(directory / "engine/snapshot.json")
    if record["dataset"] != dataset_metadata(snapshot):
        raise ValueError("dataset metadata differs from saved snapshot")
    nav = [
        _load_json(line, "nav.jsonl")
        for line in (directory / "engine/nav.jsonl").read_bytes().splitlines()
    ]
    if record["metrics"] != metrics_from({"nav": nav}, audit):
        raise ValueError("metrics differ from verified artifacts")
    if record["seed"] is not None:
        raise ValueError("deterministic F1 has no random seed")
    return record


def reproduce(directory: Path, output: Path) -> dict:
    record = read_verified(directory)
    if record["source_files"] != source_identity():
        raise ValueError("source mismatch: restore the recorded checkout before reproduction")
    current = environment()
    if any(record["environment"][key] != current[key] for key in ("python", "implementation")):
        raise ValueError("Python runtime mismatch: use the recorded runtime")
    reproduced = run_experiment(
        Path(directory) / "engine/snapshot.json", record["request"]["decision_at"], output
    )
    # IDs/time/platform/git dirtiness describe attempts; engine bytes must match.
    if reproduced["artifacts"] != record["artifacts"] or reproduced["metrics"] != record["metrics"]:
        reproduced["status"] = "FAILED"
        reproduced["error"] = {"type": "ReproductionMismatch", "message": "outputs differ"}
        save_record(Path(output), reproduced)
        raise ValueError("reproduction differs from recorded outputs")
    return reproduced


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    run.add_argument("--decision-at", default=DEFAULT_DECISION)
    run.add_argument("--output", type=Path)
    replay = commands.add_parser("reproduce")
    replay.add_argument("directory", type=Path)
    replay.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "run":
            output = args.output or ROOT / ".runs" / str(uuid.uuid4())
            result = run_experiment(args.snapshot, args.decision_at, output)
        else:
            output = args.output
            result = reproduce(args.directory, output)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"experiment failed: {exc}\n")
    print(
        json.dumps(
            {
                "directory": str(output.resolve()),
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "metrics": result["metrics"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
