"""Causal and accounting counterexamples for the F1 review."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from qtre.backtest import F1Config, run_f1
from qtre.data.snapshot import parse_snapshot


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_v1.json"
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class ExecutionReviewTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def run_fixture(self, config=F1Config()):
        return run_f1(parse_snapshot(self.payload), decision_at=DECISION, config=config)

    def test_cost_rubrics_reconcile_and_match_manual_debits(self):
        result = self.run_fixture()
        expected = {"SYN-001": "9884.81", "SYN-002": "9872.79", "SYN-003": "9870.79",
                    "SYN-004": "9881.81", "SYN-005": "9874.79"}
        for fill in result["fills"]:
            self.assertEqual(fill["cash_debit"], Decimal(expected[fill["instrument_id"]]))
            self.assertEqual(fill["notional_brl"], fill["reference_notional"] + fill["spread_cost"] + fill["slippage_cost"])
            self.assertEqual(fill["cash_debit"], fill["notional_brl"] + fill["fees"])
            self.assertGreaterEqual(fill["slippage_cost"], 0)
        self.assertEqual(Decimal("100000") + sum(r["cash_delta"] for r in result["ledger"]), result["nav"][-1]["cash_brl"])

    def test_dated_suspension_blocks_fill_even_when_open_says_tradable(self):
        old = self.payload["memberships"][0]
        suspended = dict(old, valid_from="2025-02-03", valid_to=None, status="suspended")
        old["valid_to"] = "2025-02-02"
        self.payload["memberships"].append(suspended)
        result = self.run_fixture()
        self.assertFalse(any(f["instrument_id"] == "SYN-001" for f in result["fills"]))

    def test_actual_close_clock_is_used_instead_of_replacing_minutes(self):
        for session in self.payload["calendar"]["sessions"]:
            if session["session"] >= "2025-02-03":
                session["close_at"] = session["close_at"].replace("20:00", "20:30")
        for bar in self.payload["bars"]:
            if bar["session"] >= "2025-02-03":
                bar.update(observed_at=bar["session"]+"T20:30:00Z", available_at=bar["session"]+"T20:35:00Z",
                           ingested_at=bar["session"]+"T20:36:00Z")
        result = self.run_fixture()
        self.assertEqual(result["nav"][0]["status"], "COMPLETE")
        self.assertEqual(result["nav"][0]["valued_at"].minute, 36)

    def test_late_split_blocks_evaluation_instead_of_erasing_half_the_position(self):
        self.payload["actions"][0].update(available_at="2025-02-04T15:00:00Z", ingested_at="2025-02-04T15:01:00Z")
        with self.assertRaisesRegex(ValueError, "late corporate action SYN-SPLIT"):
            self.run_fixture()

    def test_pending_order_is_cancelled_at_split_and_cost_basis_is_conserved(self):
        for bar in self.payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and bar["session"] <= "2025-01-31":
                bar["volume_shares"] = 1000
        result = self.run_fixture()
        buys = [f for f in result["fills"] if f["instrument_id"] == "SYN-001"]
        self.assertEqual([f["quantity"] for f in buys], [50])
        state = next(s for s in result["order_states"] if s["instrument_id"] == "SYN-001")
        self.assertEqual(state["status"], "CANCELLED")
        split = next(r for r in result["ledger"] if r["kind"] == "split")
        self.assertEqual(split["quantity"], 100)
        self.assertEqual(split["cost_basis"], buys[0]["cash_debit"])

    def test_capacity_is_chronological_not_json_order(self):
        for bar in self.payload["bars"]:
            if bar["session"] < "2024-07-01":
                bar["volume_shares"] = 1
        before = self.run_fixture()
        self.payload["bars"].reverse()
        after = self.run_fixture()
        for field in ("orders", "fills", "ledger", "nav"):
            self.assertEqual(before[field], after[field])

    def test_changed_future_opens_cannot_rewrite_original_orders(self):
        before = self.run_fixture()
        for event in self.payload["opens"]:
            if event["session"] >= "2025-02-03":
                event["open_price"] = 100000
        after = self.run_fixture()
        self.assertEqual(before["signals"], after["signals"])
        self.assertEqual(before["orders"], after["orders"])
        self.assertNotEqual(before["order_states"], after["order_states"])
        self.assertTrue(all(row["cash_brl"] >= 0 for row in after["nav"]))

    def test_delayed_open_publication_cannot_fill_retroactively(self):
        for event in self.payload["opens"]:
            if event["instrument_id"] == "SYN-003" and event["session"] == "2025-02-03":
                event.update(available_at="2025-02-03T13:01:00Z", ingested_at="2025-02-03T13:02:00Z")
        fill = next(f for f in self.run_fixture()["fills"] if f["instrument_id"] == "SYN-003")
        self.assertEqual(fill["session"], "2025-02-04")

    def test_expiry_and_lots_on_partial_fills(self):
        for bar in self.payload["bars"]:
            if bar["session"] <= "2025-01-31":
                bar["volume_shares"] = 2500
        result = self.run_fixture(replace(F1Config(), lot=100))
        self.assertTrue(all(f["quantity"] % 100 == 0 for f in result["fills"]))
        state = next(s for s in result["order_states"] if s["instrument_id"] == "SYN-004")
        self.assertEqual((state["status"], state["filled"], state["remaining"]), ("FILLED", 200, 0))
        self.payload["opens"] = [r for r in self.payload["opens"] if r["instrument_id"] != "SYN-003"]
        result = self.run_fixture()
        state = next(s for s in result["order_states"] if s["instrument_id"] == "SYN-003")
        self.assertEqual(state["status"], "EXPIRED")

    def test_nonfinite_and_fractional_configuration_is_rejected(self):
        for config in (replace(F1Config(), lot=1.5), replace(F1Config(), lot=True),
                       replace(F1Config(), half_spread_bps=Decimal("NaN")),
                       replace(F1Config(), fees_bps=Decimal("Infinity")),
                       replace(F1Config(), initial_cash=Decimal("0.001"))):
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.run_fixture(config)

    def test_unresolved_delisting_never_gets_a_complete_nav(self):
        action = dict(self.payload["actions"][0], action_id="DELIST", kind="delisting")
        del action["ratio"]
        self.payload["actions"].append(action)
        self.assertEqual(self.run_fixture()["nav"][-1]["status"], "NAV_INCOMPLETO")

    def test_cash_fallback_and_stable_manifest_include_code(self):
        self.payload["memberships"].pop()
        result = self.run_fixture()
        self.assertEqual(result["portfolio_reason"], "fewer_than_five_eligible")
        self.assertFalse(result["orders"])
        self.assertEqual(result["nav"][-1]["nav_brl"], Decimal("100000"))
        with localcontext() as ctx:
            ctx.prec = 6
            self.assertEqual(result, self.run_fixture())
        with patch("qtre.backtest._code_hash", return_value="different-code"):
            self.assertNotEqual(result["manifest"]["run_id"], self.run_fixture()["manifest"]["run_id"])
