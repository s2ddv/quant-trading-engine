"""Four desired invariants that fail on QTRE f99069d; review evidence only.

Run from the reviewed repository root with Python 3.10+.
No source changes: all generated runs are in TemporaryDirectory.
"""

# ruff: noqa: E402  # This standalone script adds the local src directory first.
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot, parse_snapshot
from qtre.reporting import write_f1_run
from qtre.validation import audit_f1_run
from qtre.validation.comparative_report import read_comparative_report, report_json
from qtre.validation.ml_examples import Factor, factor_as_of

DECISION = datetime.fromisoformat("2025-01-31T20:07:00+00:00")


class ReviewCounterexamples(unittest.TestCase):
    def test_01_audit_rejects_unavailable_signal_input_even_after_rehash(self):
        payload = json.loads((ROOT / "examples/synthetic_f1_v1.json").read_text())
        result = run_f1(parse_snapshot(payload), decision_at=DECISION)
        bar = next(
            b
            for b in payload["bars"]
            if b["instrument_id"] == "SYN-001" and b["session"] == "2024-01-31"
        )
        bar.update(available_at="2025-02-03T20:05:00Z", ingested_at="2025-02-03T20:06:00Z")
        snapshot = parse_snapshot(payload)
        legitimate = run_f1(snapshot, decision_at=DECISION)
        self.assertEqual(len(legitimate["orders"]), 0)
        result = deepcopy(result)
        manifest = result["manifest"]
        manifest["snapshot_hash"] = snapshot.content_hash
        del manifest["run_id"]
        manifest["run_id"] = sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with TemporaryDirectory() as temporary:
            root = write_f1_run(snapshot, result, Path(temporary) / "rehashed")
            self.assertEqual(
                audit_f1_run(root)["status"],
                "INVALID",
                "Audit accepted five orders; a causal rerun creates zero",
            )

    def test_02_comparative_reader_ignores_caller_decimal_precision(self):
        source = ROOT / "examples/f2_cost_sensitivity_v1"
        with localcontext() as ctx:
            ctx.prec = 28
            expected = report_json(read_comparative_report(source))
        with localcontext() as ctx:
            ctx.prec = 50
            self.assertEqual(report_json(read_comparative_report(source)), expected)

    def test_03_explicit_delayed_formation_produces_auditable_orders(self):
        snapshot = load_snapshot(ROOT / "examples/synthetic_f1_monthly_v1.json")
        result = run_f1(
            snapshot,
            decision_at=datetime.fromisoformat("2025-02-03T20:07:00+00:00"),
            formation_session="2025-01-31",
        )
        with TemporaryDirectory() as temporary:
            root = write_f1_run(snapshot, result, Path(temporary) / "delayed")
            audit = audit_f1_run(root)
            self.assertEqual(audit["status"], "VALID", str(audit["findings"]))

    def test_04_conflicting_revision_tie_is_rejected(self):
        instant = datetime.fromisoformat("2026-02-27T18:00:00+00:00")
        first = Factor("A", "momentum", Decimal("0.10"), "source", "v1", instant, instant)
        second = replace(first, value=Decimal("0.90"), source_version="v2")
        # With no authoritative revision sequence, contradictory simultaneous
        # versions must not be silently resolved by input enumeration order.
        with self.assertRaises(ValueError):
            factor_as_of((first, second), instant)


if __name__ == "__main__":
    unittest.main(verbosity=2)
