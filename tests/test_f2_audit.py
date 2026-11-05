"""Valid and deliberately leaked synthetic artifact fixtures."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qtre.backtest import run_f1_monthly
from qtre.data.snapshot import parse_snapshot
from qtre.reporting import _json, replay_f1, write_f1_run
from qtre.validation import audit_f1_run

import test_f1_monthly


class AuditTests(unittest.TestCase):
    def build_four_cycles(self, directory):
        case = test_f1_monthly.MonthlyTests()
        case.setUp()
        decisions = case.extend_to_fourth()
        snapshot = parse_snapshot(case.payload)
        result = run_f1_monthly(snapshot, decision_ats=decisions)
        return write_f1_run(snapshot, result, directory)

    def test_valid_four_cycle_fixture_has_stable_report(self):
        with TemporaryDirectory() as tmp:
            root = self.build_four_cycles(Path(tmp) / "valid")
            report = audit_f1_run(root)
            saved = (root / "audit.json").read_bytes()
            self.assertEqual(report["status"], "VALID")
            self.assertEqual(report["counts"]["decisions"], 4)
            self.assertEqual(report["counts"]["incomplete_nav"], 1)
            self.assertEqual(report, audit_f1_run(root))
            self.assertEqual(saved, (root / "audit.json").read_bytes())
            self.assertEqual(report["run_id"], replay_f1(root)["run_id"])

    def test_future_bar_in_order_inputs_is_rejected_even_with_valid_hashes(self):
        with TemporaryDirectory() as tmp:
            root = self.build_four_cycles(Path(tmp) / "leaked")
            orders_path = root / "orders.jsonl"
            orders = [json.loads(line) for line in orders_path.read_text().splitlines()]
            first = orders[0]
            first["input_keys"].append(f"bar:{first['instrument_id']}:2025-04-30")
            orders_path.write_bytes(b"".join(_json(row) + b"\n" for row in orders))
            manifest_path = root / "manifest.json"
            envelope = json.loads(manifest_path.read_text())
            envelope["files"]["orders.jsonl"] = sha256(orders_path.read_bytes()).hexdigest()
            manifest_path.write_bytes(_json(envelope) + b"\n")
            # The F1 book replay remains sound; the separate F2 check catches
            # an input that was unavailable when the order was created.
            replay_f1(root)
            report = audit_f1_run(root)
            self.assertEqual(report["status"], "INVALID")
            self.assertIn("available after use", report["findings"][0])
            self.assertEqual(json.loads((root / "audit.json").read_text()), report)

    def test_replay_integrity_failure_is_reported(self):
        with TemporaryDirectory() as tmp:
            root = self.build_four_cycles(Path(tmp) / "corrupt")
            with (root / "orders.jsonl").open("ab") as stream:
                stream.write(b"\n")
            report = audit_f1_run(root)
            self.assertEqual(report["status"], "INVALID")
            self.assertIn("SHA-256", report["findings"][0])


if __name__ == "__main__":
    unittest.main()
