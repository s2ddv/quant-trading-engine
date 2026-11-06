"""Synthetic F2 controls share the F1 calendar and independent replay."""

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from dataclasses import replace
from unittest.mock import patch

from qtre.backtest import F1Config, run_f1_monthly, run_f2_control
from qtre.data.snapshot import parse_snapshot
from qtre.reporting import ReplayError, _json, replay_f1, write_f1_run
from qtre.validation import audit_f1_run

from test_f1_monthly import MonthlyTests


def four_cycles():
    case = MonthlyTests()
    case.setUp()
    decisions = case.extend_to_fourth()
    return parse_snapshot(case.payload), decisions


def change_hashed_table(root, name, change):
    path = root / name
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    change(rows)
    path.write_bytes(b"".join(_json(row) + b"\n" for row in rows))
    manifest_path = root / "manifest.json"
    envelope = json.loads(manifest_path.read_bytes())
    envelope["files"][name] = sha256(path.read_bytes()).hexdigest()
    manifest_path.write_bytes(_json(envelope) + b"\n")


class ControlTests(unittest.TestCase):
    def test_cash_has_own_identity_and_constant_nav(self):
        snapshot, decisions = four_cycles()
        result = run_f2_control(snapshot, decision_ats=decisions, control_id="cash")
        self.assertEqual(result["manifest"]["control_id"], "cash")
        self.assertEqual(len(result["manifest"]["decision_windows"]), 4)
        for table in ("orders", "order_states", "fills", "ledger"):
            self.assertEqual(result[table], ())
        self.assertTrue(result["nav"])
        for row in result["nav"]:
            self.assertEqual(row["nav_brl"], Decimal("100000.00"))
            self.assertEqual(row["cash_brl"], Decimal("100000"))
            self.assertEqual(row["marks"], {})
        with TemporaryDirectory() as tmp:
            root = write_f1_run(snapshot, result, Path(tmp) / "cash")
            rebuilt = replay_f1(root)
            self.assertEqual(rebuilt["run_id"], result["manifest"]["run_id"])
            self.assertEqual(rebuilt["nav"][-1]["nav_brl"], "100000.00")
            self.assertEqual(audit_f1_run(root)["status"], "VALID")

    def test_cash_replay_rejects_rehashed_order(self):
        snapshot, decisions = four_cycles()
        result = run_f2_control(snapshot, decision_ats=decisions, control_id="cash")
        with TemporaryDirectory() as tmp:
            root = write_f1_run(snapshot, result, Path(tmp) / "cash")
            change_hashed_table(root, "orders.jsonl", lambda rows: rows.append({"run_id": result["manifest"]["run_id"]}))
            with self.assertRaisesRegex(ReplayError, "cash control cannot trade"):
                replay_f1(root)

    def test_equal_weight_has_own_artifacts_and_reconciled_book(self):
        snapshot, decisions = four_cycles()
        cash = run_f2_control(snapshot, decision_ats=decisions, control_id="cash")
        equal = run_f2_control(snapshot, decision_ats=decisions, control_id="equal_weight")
        self.assertNotEqual(equal["manifest"]["run_id"], cash["manifest"]["run_id"])
        self.assertEqual(len(equal["manifest"]["decision_windows"]), 4)
        self.assertTrue(equal["orders"])
        self.assertTrue(equal["fills"])
        self.assertTrue(all(row["target_weight"] == Decimal("0.10") for row in equal["orders"]))
        self.assertTrue(all(row["created_at"] < row["earliest_execution_at"] for row in equal["orders"]))
        with TemporaryDirectory() as tmp:
            root = write_f1_run(snapshot, equal, Path(tmp) / "equal")
            rebuilt = replay_f1(root)
            self.assertEqual(rebuilt["run_id"], equal["manifest"]["run_id"])
            self.assertEqual(rebuilt["cash_brl"], equal["nav"][-1]["cash_brl"])
            self.assertEqual(audit_f1_run(root)["status"], "VALID")

    def test_equal_weight_audit_rejects_rehashed_wrong_target(self):
        snapshot, decisions = four_cycles()
        result = run_f2_control(snapshot, decision_ats=decisions, control_id="equal_weight")
        with TemporaryDirectory() as tmp:
            root = write_f1_run(snapshot, result, Path(tmp) / "equal")
            change_hashed_table(root, "orders.jsonl", lambda rows: rows[0].update(target_weight="0.50"))
            self.assertEqual(replay_f1(root)["control_id"], "equal_weight")
            report = audit_f1_run(root)
            self.assertEqual(report["status"], "INVALID")
            self.assertIn("equal weight target mismatch", report["findings"][0])

    def test_equal_weight_uses_all_eligible_even_below_momentum_minimum(self):
        snapshot, decisions = four_cycles()
        from qtre.signals import momentum_12_2

        def four_eligible(*args, **kwargs):
            return tuple(replace(s, eligible=False) if s.instrument_id == "SYN-005" else s
                         for s in momentum_12_2(*args, **kwargs))

        with patch("qtre.backtest.momentum_12_2", side_effect=four_eligible), \
             patch("qtre.backtest.rebalance.momentum_12_2", side_effect=four_eligible):
            equal = run_f1_monthly(snapshot, decision_ats=decisions[:2], control_id="equal_weight")
            momentum = run_f1_monthly(snapshot, decision_ats=decisions[:2])
        self.assertEqual({o["instrument_id"] for o in equal["orders"][:4]},
                         {"SYN-001", "SYN-002", "SYN-003", "SYN-004"})
        self.assertTrue(equal["fills"])
        self.assertEqual(momentum["orders"], ())

    def test_equal_weight_stays_in_cash_with_no_eligible_names(self):
        snapshot, decisions = four_cycles()
        from qtre.signals import momentum_12_2

        def none_eligible(*args, **kwargs):
            return tuple(replace(s, eligible=False) for s in momentum_12_2(*args, **kwargs))

        with patch("qtre.backtest.momentum_12_2", side_effect=none_eligible), \
             patch("qtre.backtest.rebalance.momentum_12_2", side_effect=none_eligible):
            result = run_f1_monthly(snapshot, decision_ats=decisions, control_id="equal_weight")
        self.assertEqual(result["orders"], ())
        self.assertTrue(all(row["nav_brl"] == Decimal("100000.00") for row in result["nav"]))

    def test_equal_weight_respects_lots_capacity_and_cash(self):
        snapshot, decisions = four_cycles()
        config = F1Config(lot=10, max_participation=Decimal("0.001"))
        result = run_f2_control(snapshot, decision_ats=decisions, control_id="equal_weight",
                                config=config)
        orders = {row["order_id"]: row for row in result["orders"]}
        self.assertTrue(result["fills"])
        for fill in result["fills"]:
            self.assertEqual(fill["quantity"] % 10, 0)
            self.assertLessEqual(fill["quantity"], orders[fill["order_id"]]["capacity_shares"])
        self.assertTrue(all(row["cash_brl"] >= 0 for row in result["nav"]))
        with TemporaryDirectory() as tmp:
            root = write_f1_run(snapshot, result, Path(tmp) / "capacity")
            self.assertEqual(replay_f1(root)["cash_brl"], result["nav"][-1]["cash_brl"])

    def test_future_opens_change_fills_but_not_equal_weight_orders(self):
        snapshot, decisions = four_cycles()
        before = run_f1_monthly(snapshot, decision_ats=decisions, control_id="equal_weight")
        case = MonthlyTests()
        case.setUp()
        case.extend_to_fourth()
        for opening in case.payload["opens"]:
            if opening["session"] >= "2025-02-03":
                opening["open_price"] = 100000
        after = run_f1_monthly(parse_snapshot(case.payload), decision_ats=decisions,
                               control_id="equal_weight")
        self.assertEqual(tuple(o for o in before["orders"] if o["order_id"].startswith("O-")),
                         tuple(o for o in after["orders"] if o["order_id"].startswith("O-")))
        self.assertNotEqual(before["fills"], after["fills"])


if __name__ == "__main__":
    unittest.main()
