"""F2 summaries must not turn incomplete synthetic NAV into a return."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from decimal import Decimal

from qtre.validation.summary import summarize_f1_run
from qtre.reporting import ReplayError

from test_f2_audit import AuditTests


class SummaryTests(unittest.TestCase):
    def test_four_cycle_summary_preserves_incomplete_nav(self):
        with TemporaryDirectory() as tmp:
            root = AuditTests().build_four_cycles(Path(tmp) / "run")
            summary = summarize_f1_run(root)
            self.assertEqual(summary["decisions"], 4)
            self.assertEqual(summary["orders"], 16)
            self.assertEqual(summary["fills"], 16)
            self.assertEqual(summary["sessions"], 66)
            self.assertEqual(summary["incomplete_sessions"], ["2025-02-04"])
            self.assertIsNone(summary["cumulative_return"])
            self.assertEqual(summary["return_status"], "UNAVAILABLE_INCOMPLETE_NAV")
            self.assertEqual(summary["final_cash_brl"], Decimal("50712.22"))
            self.assertEqual(summary["costs_brl"], {
                "spread_cost": Decimal("30.27"),
                "slippage_cost": Decimal("30.24"),
                "fees": Decimal("30.27"),
                "total": Decimal("90.78"),
            })
            self.assertEqual(summary, summarize_f1_run(root))

    def test_tampered_run_is_rejected_before_summary(self):
        with TemporaryDirectory() as tmp:
            root = AuditTests().build_four_cycles(Path(tmp) / "run")
            with (root / "fills.jsonl").open("ab") as stream:
                stream.write(b"\n")
            with self.assertRaises(ReplayError):
                summarize_f1_run(root)


if __name__ == "__main__":
    unittest.main()
