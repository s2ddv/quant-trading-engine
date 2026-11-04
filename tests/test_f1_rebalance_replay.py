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

    def test_schema_three_replays_sale_without_running_engine(self):
        manifest = json.loads((self.path / "manifest.json").read_text())
        self.assertEqual(manifest["artifact_schema_version"], 3)
        second = write_f1_run(self.snapshot, self.result, Path(self.temp.name) / "repeat")
        for file in self.path.iterdir():
            self.assertEqual(file.read_bytes(), (second / file.name).read_bytes())
        with patch("qtre.backtest.run_f1", side_effect=AssertionError("engine called")):
            replayed = replay_f1(self.path)
        self.assertEqual(replayed["positions"]["SYN-001"], 503)
        self.assertEqual(replayed["cost_basis"]["SYN-001"], Decimal("7556.32"))
        self.assertEqual(replayed["cash_brl"], Decimal("50432.20"))
        self.assertEqual(next(row for row in replayed["nav"] if row["session"] == "2025-03-03")["nav_brl"],
                         "100755.20")

    def test_previous_schema_two_remains_readable(self):
        previous = dict(self.result)
        manifest = dict(previous["manifest"])
        manifest.pop("bridge_sessions")
        manifest.update(schema_version=3, model_id="synthetic-f1-two-formations-v1")
        manifest.pop("run_id")
        manifest["run_id"] = sha256(json.dumps(manifest, sort_keys=True,
                                                separators=(",", ":")).encode()).hexdigest()
        previous["manifest"] = manifest
        expected_days = {"2025-02-03", "2025-02-04", "2025-02-05", "2025-02-28",
                         "2025-03-03", "2025-03-04", "2025-03-05"}
        previous["nav"] = tuple(row for row in previous["nav"] if row["session"] in expected_days)
        path = write_f1_run(self.snapshot, previous, Path(self.temp.name) / "previous-schema")
        self.assertEqual(json.loads((path / "manifest.json").read_text())["artifact_schema_version"], 2)
        self.assertEqual(replay_f1(path)["nav"][-1]["nav_brl"], "100755.20")

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
        self._change_and_rehash("nav.jsonl", lambda rows: next(row for row in rows if row["session"] == "2025-03-03")
                                .update(nav_brl="100755.21"))
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

    def test_unpaid_dividend_crosses_formation_and_pays_before_trades(self):
        payload = json.loads(FIXTURE.read_text())
        dividend = next(a for a in payload["actions"] if a["action_id"] == "SYN-DIV")
        dividend["pay_session"] = "2025-03-03"
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST,
                                       second_decision_at=SECOND)
        self.assertEqual(result["nav"][2]["cash_brl"], Decimal("50615.01"))
        self.assertEqual(result["nav"][2]["receivable_brl"], Decimal("159.00"))
        formation = next(row for row in result["nav"] if row["session"] == "2025-02-28")
        self.assertEqual(formation["nav_brl"], Decimal("100765.01"))
        self.assertEqual(formation["receivable_brl"], Decimal("159.00"))
        second_events = [row for row in result["ledger"] if row["session"] == "2025-03-03"]
        self.assertEqual((second_events[0]["kind"], second_events[0]["cash_delta"]),
                         ("dividend_pay", Decimal("159.00")))
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "delayed-dividend")
        with patch("qtre.backtest.run_f1", side_effect=AssertionError("engine called")):
            rebuilt = replay_f1(path)
        self.assertEqual(rebuilt["cash_brl"], Decimal("50432.20"))
        self.assertEqual(rebuilt["receivables"], {})
        self.assertEqual(next(row for row in rebuilt["nav"] if row["session"] == "2025-02-28")["receivable_brl"],
                         "159.00")

    def test_unpaid_dividend_does_not_become_early_cash(self):
        payload = json.loads(FIXTURE.read_text())
        next(a for a in payload["actions"] if a["action_id"] == "SYN-DIV")["pay_session"] = "2025-03-05"
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST,
                                       second_decision_at=SECOND)
        self.assertEqual(next(row for row in result["nav"] if row["session"] == "2025-03-03")["receivable_brl"],
                         Decimal("159.00"))
        self.assertFalse(any(row["kind"] == "dividend_pay" and row["session"] < "2025-03-05"
                             for row in result["ledger"]))
        self.assertEqual(result["nav"][-1]["receivable_brl"], Decimal(0))
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "late-payment")
        rebuilt = replay_f1(path)
        self.assertEqual(next(row for row in rebuilt["nav"] if row["session"] == "2025-03-03")["receivable_brl"],
                         "159.00")
        self.assertEqual(rebuilt["receivables"], {})

    def test_payment_between_windows_is_marked_and_replayed(self):
        payload = json.loads(FIXTURE.read_text())
        next(a for a in payload["actions"] if a["action_id"] == "SYN-DIV")["pay_session"] = "2025-02-10"
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST,
                                       second_decision_at=SECOND)
        before = next(row for row in result["nav"] if row["session"] == "2025-02-07")
        paid = next(row for row in result["nav"] if row["session"] == "2025-02-10")
        self.assertEqual((before["cash_brl"], before["receivable_brl"]),
                         (Decimal("50615.01"), Decimal("159.00")))
        self.assertEqual((paid["cash_brl"], paid["receivable_brl"], paid["nav_brl"]),
                         (Decimal("50774.01"), Decimal(0), Decimal("100085.01")))
        self.assertEqual(next(row for row in result["ledger"] if row["event_id"] == "SYN-DIV-pay")["session"],
                         "2025-02-10")
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "intermediate-payment")
        with patch("qtre.backtest.run_f1", side_effect=AssertionError("engine called")):
            rebuilt = replay_f1(path)
        self.assertEqual(next(row for row in rebuilt["nav"] if row["session"] == "2025-02-10")["nav_brl"],
                         "100085.01")

    def test_late_intermediate_action_is_rejected(self):
        payload = json.loads(FIXTURE.read_text())
        late = dict(next(a for a in payload["actions"] if a["action_id"] == "SYN-DIV"))
        late.update(action_id="SYN-LATE", ex_session="2025-02-10", pay_session="2025-02-12",
                    observed_at="2025-02-10T18:00:00Z", announced_at="2025-02-10T18:00:00Z",
                    available_at="2025-02-10T18:01:00Z", ingested_at="2025-02-10T18:02:00Z")
        payload["actions"].append(late)
        with self.assertRaisesRegex(ValueError, "late corporate action SYN-LATE"):
            run_f1_two_formations(parse_snapshot(payload), first_decision_at=FIRST,
                                  second_decision_at=SECOND)

    def test_intermediate_split_preserves_nav_and_replays(self):
        payload = json.loads(FIXTURE.read_text())
        split = dict(next(a for a in payload["actions"] if a["action_id"] == "SYN-SPLIT"))
        split.update(action_id="SYN-SPLIT-2", ex_session="2025-02-10",
                     announced_at="2025-02-07T18:00:00Z", observed_at="2025-02-07T18:00:00Z",
                     available_at="2025-02-07T18:01:00Z", ingested_at="2025-02-07T18:02:00Z")
        payload["actions"].append(split)
        for bar in payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and bar["session"] >= "2025-02-10":
                for field in ("open", "high", "low", "close"):
                    bar[field] /= 2
        for opening in payload["opens"]:
            if opening["instrument_id"] == "SYN-001" and opening["session"] >= "2025-02-10":
                opening["open_price"] /= 2
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST,
                                       second_decision_at=SECOND)
        marked = next(row for row in result["nav"] if row["session"] == "2025-02-10")
        self.assertEqual(marked["marks"]["SYN-001"]["quantity"], 1316)
        self.assertEqual(marked["nav_brl"], Decimal("100085.01"))
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "intermediate-split")
        rebuilt = replay_f1(path)
        self.assertEqual(next(row for row in rebuilt["nav"] if row["session"] == "2025-02-10")["nav_brl"],
                         "100085.01")

    def test_missing_intermediate_mark_is_explicit_and_replays(self):
        payload = json.loads(FIXTURE.read_text())
        payload["bars"] = [bar for bar in payload["bars"]
                           if not (bar["instrument_id"] == "SYN-003" and bar["session"] == "2025-02-10")]
        snapshot = parse_snapshot(payload)
        result = run_f1_two_formations(snapshot, first_decision_at=FIRST,
                                       second_decision_at=SECOND)
        marked = next(row for row in result["nav"] if row["session"] == "2025-02-10")
        self.assertEqual((marked["status"], marked["missing_marks"], marked["nav_brl"]),
                         ("NAV_INCOMPLETO", ["SYN-003"], None))
        path = write_f1_run(snapshot, result, Path(self.temp.name) / "missing-intermediate")
        rebuilt = replay_f1(path)
        self.assertEqual(next(row for row in rebuilt["nav"] if row["session"] == "2025-02-10")["status"],
                         "NAV_INCOMPLETO")


if __name__ == "__main__":
    unittest.main()
