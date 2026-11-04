"""Artifact schema 2 replay of the second formation and sale."""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from qtre.backtest import run_f1_two_formations
from qtre.data.snapshot import load_snapshot, parse_snapshot
from qtre.reporting import ReplayError, replay_f1, write_f1_run


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_rebalance_v1.json"
FIRST = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)
SECOND = datetime(2025, 2, 28, 20, 7, tzinfo=timezone.utc)


class RebalanceReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.snapshot = load_snapshot(FIXTURE)
        self.result = run_f1_two_formations(self.snapshot, first_decision_at=FIRST,
                                            second_decision_at=SECOND)
        self.path = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "run")

    def _change_and_rehash(self, name, change):
        path = self.path / name
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        change(rows)
        path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
                                for row in rows))
        manifest_path = self.path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][name] = sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")

    def test_schema_two_replays_sale_without_running_engine(self):
        manifest = json.loads((self.path / "manifest.json").read_text())
        self.assertEqual(manifest["artifact_schema_version"], 2)
        second = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "repeat")
        for file in self.path.iterdir():
            self.assertEqual(file.read_bytes(), (second / file.name).read_bytes())
        with patch("qtre.backtest.run_f1", side_effect=AssertionError("engine called")):
            replayed = replay_f1(self.path)
        self.assertEqual(replayed["positions"]["SYN-001"], 503)
        self.assertEqual(replayed["cost_basis"]["SYN-001"], Decimal("7556.32"))
        self.assertEqual(replayed["cash_brl"], Decimal("50432.20"))
        self.assertEqual(replayed["nav"][4]["nav_brl"], "100755.20")

    def test_rehashed_sale_basis_tamper_is_rejected(self):
        self._change_and_rehash("fills.jsonl", lambda rows: next(row for row in rows if row.get("side") == "sell")
                                .update(basis_removed="1.00"))
        with self.assertRaisesRegex(ReplayError, "sale basis removed"):
            replay_f1(self.path)

    def test_missing_file_and_rehashed_nav_tamper_are_rejected(self):
        (self.path / "ledger.jsonl").unlink()
        with self.assertRaisesRegex(ReplayError, "missing or unreadable"):
            replay_f1(self.path)
        self.path = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "again")
        self._change_and_rehash("nav.jsonl", lambda rows: rows[4].update(nav_brl="100755.21"))
        with self.assertRaisesRegex(ReplayError, "NAV 2025-03-03"):
            replay_f1(self.path)

    def test_partial_sale_replays_with_remaining_order(self):
        payload = json.loads(FIXTURE.read_text())
        for bar in payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and "2025-02-06" <= bar["session"] <= "2025-02-28":
                bar["volume_shares"] = 1000
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST, second_decision_at=SECOND)
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "partial")
        rebuilt = replay_f1(path)
        self.assertEqual(rebuilt["positions"]["SYN-001"], 508)


if __name__ == "__main__":
    unittest.main()
