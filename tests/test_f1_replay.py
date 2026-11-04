"""Persisted synthetic F1 runs and independently reconciled replay."""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from hashlib import sha256

from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot
from qtre.reporting import ReplayError, replay_f1, write_f1_run


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_v1.json"
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class F1ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.snapshot = load_snapshot(FIXTURE)
        self.result = run_f1(self.snapshot, decision_at=DECISION)
        self.path = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "run")

    def _rewrite_with_hash(self, name, change):
        path = self.path / name
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        change(rows)
        path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows))
        manifest_path = self.path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][name] = sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")

    def test_deterministic_bytes_and_independent_replay(self):
        second = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "second")
        for path in self.path.iterdir():
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
        with patch("qtre.backtest.run_f1", side_effect=AssertionError("replay called engine")):
            rebuilt = replay_f1(self.path)
        self.assertEqual(rebuilt["cash_brl"], Decimal("50774.01"))
        self.assertEqual(rebuilt["positions"]["SYN-001"], 658)
        self.assertEqual(rebuilt["receivables"], {})
        self.assertEqual(rebuilt["nav"][-1]["nav_brl"], "100085.01")
        with self.assertRaises(FileExistsError):
            write_f1_run(self.snapshot, self.result, self.path)

    def test_missing_and_altered_artifact(self):
        (self.path / "orders.jsonl").unlink()
        with self.assertRaisesRegex(ReplayError, "missing or unreadable"):
            replay_f1(self.path)
        self.path = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "again")
        path = self.path / "fills.jsonl"
        path.write_bytes(path.read_bytes().replace(b"9884.81", b"9884.82"))
        with self.assertRaisesRegex(ReplayError, "SHA-256"):
            replay_f1(self.path)

    def test_cost_rubrics_checked_even_if_file_hash_updated(self):
        self._rewrite_with_hash("fills.jsonl", lambda rows: rows[0].update(spread_cost="0.01"))
        with self.assertRaisesRegex(ReplayError, "spread"):
            replay_f1(self.path)

    def test_incomplete_nav_is_reproduced_and_not_imputed(self):
        rebuilt = replay_f1(self.path)
        middle = rebuilt["nav"][1]
        self.assertEqual(middle["status"], "NAV_INCOMPLETO")
        self.assertEqual(middle["missing_marks"], ["SYN-005"])
        self.assertEqual(middle["receivable_brl"], "159.00")
        self.assertIsNone(middle["nav_brl"])
        self._rewrite_with_hash("nav.jsonl", lambda rows: rows[1].update(nav_brl="100000.00"))
        with self.assertRaisesRegex(ReplayError, "NAV 2025-02-04"):
            replay_f1(self.path)


if __name__ == "__main__":
    unittest.main()
