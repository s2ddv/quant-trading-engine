from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import unittest

from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_f1_v1.json"
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class F1BacktestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_f1(load_snapshot(FIXTURE), decision_at=DECISION)

    def test_next_open_and_cent_reconciliation(self):
        fills = self.result["fills"]
        self.assertEqual(len(fills), 5)
        self.assertTrue(all(fill["executed_at"] > DECISION for fill in fills))
        self.assertEqual(fills[0]["quantity"], 329)
        self.assertEqual(fills[0]["price"], Decimal("30.03"))
        self.assertEqual(fills[0]["fees"], Decimal("4.94"))
        self.assertEqual(self.result["nav"][0]["cash_brl"], Decimal("60498.92"))
        self.assertEqual(self.result["nav"][0]["nav_brl"], Decimal("99942.92"))
        for row in self.result["nav"]:
            if row["status"] == "COMPLETE":
                self.assertEqual(row["nav_brl"], row["cash_brl"] + row["receivable_brl"] + row["positions_value_brl"])
            self.assertGreaterEqual(row["cash_brl"], 0)

    def test_suspension_split_dividend_and_missing_mark(self):
        fills = self.result["fills"]
        self.assertEqual(next(f["session"] for f in fills if f["order_id"] == "O-SYN-004"), "2025-02-04")
        ledger = self.result["ledger"]
        self.assertEqual(next(r["quantity"] for r in ledger if r["event_id"] == "SYN-SPLIT"), 658)
        self.assertEqual(self.result["nav"][1]["status"], "NAV_INCOMPLETO")
        self.assertIsNone(self.result["nav"][1]["nav_brl"])
        self.assertEqual(self.result["nav"][1]["receivable_brl"], Decimal("159.00"))
        self.assertEqual(self.result["nav"][2]["receivable_brl"], Decimal(0))
        self.assertEqual(self.result["nav"][2]["nav_brl"], Decimal("100088.01"))


if __name__ == "__main__":
    unittest.main()
