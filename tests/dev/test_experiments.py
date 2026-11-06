"""Experiment lifecycle and reproduction must fail closed on changed evidence."""

import json
from unittest.mock import patch

import pytest

from qtre.data.snapshot import SnapshotError

from tools.qtre_experiment import (
    DEFAULT_DECISION,
    DEFAULT_SNAPSHOT,
    read_verified,
    reproduce,
    run_experiment,
)


def test_roundtrip_and_independent_replay(tmp_path):
    first = tmp_path / "first"
    original = run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, first)
    copy = reproduce(first, tmp_path / "copy")
    assert original["artifacts"] == copy["artifacts"]
    assert original["experiment_id"] != copy["experiment_id"]
    assert original["status"] == "COMPLETED"
    assert original["seed"] is None
    assert original["metrics"]["audit_status"] == "VALID"
    assert original["metrics"]["incomplete_nav"] == 1
    assert original["metrics"]["last_nav_brl"] == "100085.01"
    assert original["engine_run"]["config"]["initial_cash"] == "100000"
    assert len(original["git"]["commit"]) == 40
    assert read_verified(first)["experiment_id"] == original["experiment_id"]


def test_refuses_overwrite(tmp_path):
    output = tmp_path / "run"
    run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, output)
    before = (output / "experiment.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, output)
    assert (output / "experiment.json").read_bytes() == before


def test_failed_input_is_recorded(tmp_path):
    output = tmp_path / "failed"
    with pytest.raises(SnapshotError):
        run_experiment(tmp_path / "absent.json", DEFAULT_DECISION, output)
    record = json.loads((output / "experiment.json").read_text())
    assert record["status"] == "FAILED"
    assert record["error"]["type"] == "SnapshotError"
    with pytest.raises(ValueError, match="completed"):
        reproduce(output, tmp_path / "copy")


def test_interrupt_is_recorded(tmp_path):
    with patch("tools.qtre_experiment.run_f1", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, tmp_path / "run")
    record = json.loads((tmp_path / "run/experiment.json").read_text())
    assert record["status"] == "INTERRUPTED"


@pytest.mark.parametrize("name", ["snapshot.json", "ledger.jsonl", "audit.json"])
def test_tampering_is_rejected(tmp_path, name):
    run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, tmp_path / "run")
    with (tmp_path / "run/engine" / name).open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        reproduce(tmp_path / "run", tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_source_change_rejected_before_reproduction(tmp_path):
    run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, tmp_path / "run")
    with patch("tools.qtre_experiment.source_identity", return_value={}):
        with pytest.raises(ValueError, match="source mismatch"):
            reproduce(tmp_path / "run", tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_metadata_config_tampering_rejected(tmp_path):
    run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, tmp_path / "run")
    path = tmp_path / "run/experiment.json"
    record = json.loads(path.read_text())
    record["engine_run"]["config"]["fees_bps"] = "0"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="configuration differs"):
        reproduce(tmp_path / "run", tmp_path / "copy")


@pytest.mark.parametrize(
    "decision",
    ["2025-01-31T17:07:00-03:00", "2025-01-31T20:07:00Z", "2025-01-31T20:07:00.000000+00:00"],
)
def test_equivalent_decision_representations_reproduce(tmp_path, decision):
    original = run_experiment(DEFAULT_SNAPSHOT, decision, tmp_path / "run")
    copy = reproduce(tmp_path / "run", tmp_path / "copy")
    assert original["artifacts"] == copy["artifacts"]
    assert original["request"]["decision_at"] == DEFAULT_DECISION


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("metrics", "last_nav_brl", "999999999"),
        ("dataset", "start_session", "1900-01-01"),
    ],
)
def test_metadata_tampering_rejected_before_execution(tmp_path, section, key, value):
    run_experiment(DEFAULT_SNAPSHOT, DEFAULT_DECISION, tmp_path / "run")
    path = tmp_path / "run/experiment.json"
    record = json.loads(path.read_text())
    record[section][key] = value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="differ"):
        reproduce(tmp_path / "run", tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_timezone_required_and_failure_recorded(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        run_experiment(DEFAULT_SNAPSHOT, "2025-01-31T20:07:00", tmp_path / "run")
    assert json.loads((tmp_path / "run/experiment.json").read_text())["status"] == "FAILED"
