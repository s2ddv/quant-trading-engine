"""Hand-calculated second formation and adverse execution paths."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import unittest

from qtre.backtest import F1Config, run_f1_two_formations
from qtre.data.snapshot import parse_snapshot


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_rebalance_v1.json"
FIRST = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)
SECOND = datetime(2025, 2, 28, 20, 7, tzinfo=timezone.utc)


class RebalanceTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def run_case(self, config=F1Config()):
        return run_f1_two_formations(parse_snapshot(self.payload), first_decision_at=FIRST,
                                     second_decision_at=SECOND, config=config)

    def test_manual_sale_cost_basis_cash_and_nav(self):
        result = self.run_case()
        orders = [o for o in result["orders"] if o["order_id"].startswith("O2-")]
        self.assertEqual([(o["instrument_id"], o["side"], o["quantity"]) for o in orders],
                         [("SYN-001", "sell", 155), ("SYN-002", "buy", 7),
                          ("SYN-003", "buy", 6), ("SYN-004", "buy", 6),
                          ("SYN-005", "buy", 113)])
        self.assertTrue(all(o["created_at"] == SECOND and o["earliest_execution_at"] > SECOND for o in orders))
        fills = [f for f in result["fills"] if f["order_id"].startswith("O2-")]
        self.assertEqual([f["side"] for f in fills], ["sell", "buy", "buy", "buy", "buy"])
        sale = fills[0]
        self.assertEqual((sale["price"], sale["spread_cost"], sale["slippage_cost"], sale["fees"]),
                         (Decimal("19.980"), Decimal("1.55"), Decimal("1.55"), Decimal("1.55")))
        self.assertEqual((sale["cash_credit"], sale["basis_removed"], sale["realized_pnl"]),
                         (Decimal("3095.35"), Decimal("2328.49"), Decimal("766.86")))
        self.assertEqual([f["cash_debit"] for f in fills[1:]],
                         list(map(Decimal, ("217.33", "192.29", "198.30", "2829.24"))))
        self.assertEqual(result["nav"][3]["nav_brl"], Decimal("100765.01"))
        self.assertEqual((result["nav"][4]["cash_brl"], result["nav"][4]["positions_value_brl"],
                          result["nav"][4]["nav_brl"]),
                         (Decimal("50432.20"), Decimal("50323.00"), Decimal("100755.20")))
        basis = {e["instrument_id"]: e["cost_basis"] for e in result["ledger"]}
        self.assertEqual(basis, dict(zip(
            ("SYN-001", "SYN-002", "SYN-003", "SYN-004", "SYN-005"),
            map(Decimal, ("7556.32", "10090.12", "10063.08", "10080.11", "12704.03")))))
        self.assertEqual({ident: mark["quantity"] for ident, mark in result["nav"][4]["marks"].items()},
                         {"SYN-001": 503, "SYN-002": 325, "SYN-003": 314,
                          "SYN-004": 305, "SYN-005": 403})
        self.assertEqual(sum(f["spread_cost"] + f["slippage_cost"] + f["fees"] for f in fills), Decimal("9.81"))

    def test_future_prices_do_not_rewrite_second_orders(self):
        before = self.run_case()
        for event in self.payload["opens"]:
            if event["session"] >= "2025-03-03":
                event["open_price"] = 100000
        after = self.run_case()
        self.assertEqual(before["orders"], after["orders"])
        self.assertNotEqual(before["fills"], after["fills"])

    def test_lots_and_partial_capacity(self):
        lot_result = self.run_case(replace(F1Config(), lot=10))
        self.assertTrue(all(o["quantity"] % 10 == 0 for o in lot_result["orders"] if o["order_id"].startswith("O2-")))
        self.assertTrue(all(f["quantity"] % 10 == 0 for f in lot_result["fills"] if f["order_id"].startswith("O2-")))
        for bar in self.payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and "2025-02-06" <= bar["session"] <= "2025-02-28":
                bar["volume_shares"] = 1000
        result = self.run_case()
        sale_fills = [f["quantity"] for f in result["fills"] if f["order_id"] == "O2-SYN-001"]
        self.assertEqual(sale_fills, [50, 50, 50])
        state = next(s for s in result["order_states"] if s["order_id"] == "O2-SYN-001")
        self.assertEqual((state["status"], state["remaining"]), ("EXPIRED", 5))

    def test_suspended_sale_does_not_fund_buys(self):
        config = replace(F1Config(), max_name_weight=Decimal("0.20"))
        baseline = self.run_case(config)
        self.assertEqual(baseline["nav"][3]["cash_brl"], Decimal("1388.29"))
        for event in self.payload["opens"]:
            if event["instrument_id"] == "SYN-001" and event["session"] >= "2025-03-03":
                event["tradable"] = False
        result = self.run_case(config)
        second_fills = [f for f in result["fills"] if f["order_id"].startswith("O2-")]
        self.assertFalse(any(f["side"] == "sell" for f in second_fills))
        self.assertLessEqual(sum(f["cash_debit"] for f in second_fills), Decimal("1388.29"))
        self.assertTrue(any(s["status"] == "EXPIRED" and s["remaining"] > 0
                            for s in result["order_states"] if s["order_id"].startswith("O2-")))
        self.assertGreaterEqual(result["nav"][-1]["cash_brl"], 0)

    def test_dated_suspension_defers_sale_even_with_tradable_open(self):
        original = next(row for row in self.payload["memberships"] if row["instrument_id"] == "SYN-001")
        suspended = dict(original, valid_from="2025-03-03", valid_to="2025-03-03", status="suspended")
        restored = dict(original, valid_from="2025-03-04", valid_to=None)
        original["valid_to"] = "2025-03-02"
        self.payload["memberships"].extend((suspended, restored))
        result = self.run_case()
        sale = next(f for f in result["fills"] if f["order_id"] == "O2-SYN-001")
        self.assertEqual(sale["session"], "2025-03-04")


if __name__ == "__main__":
    unittest.main()
