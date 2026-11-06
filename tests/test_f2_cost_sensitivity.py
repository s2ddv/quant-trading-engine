"""Cost sensitivity must preserve artifacts and qualify NAV comparisons."""

from decimal import Decimal
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qtre.reporting import replay_f1
from qtre.backtest import F1Config, run_f1_monthly
from qtre.reporting import write_f1_run
from qtre.validation.cost_sensitivity import compare_pair, run_cost_sensitivity
from test_f2_controls import four_cycles


class CostSensitivityTests(unittest.TestCase):
    def test_nine_runs_replay_audit_and_reconcile(self):
        snapshot, decisions = four_cycles()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "sensitivity"
            report = run_cost_sensitivity(snapshot, decision_ats=decisions, directory=root)
            self.assertEqual(len({row["run_id"] for runs in report["runs"].values()
                                  for row in runs.values()}), 9)
            for strategy, runs in report["runs"].items():
                for scenario, row in runs.items():
                    path = root / f"{strategy}-{scenario}"
                    self.assertEqual(replay_f1(path)["run_id"], row["run_id"])
                    self.assertEqual(row["audit_status"], "VALID")
                    self.assertEqual(row["decisions"], 4)
                    self.assertEqual(row["sessions"], 66)
                    self.assertEqual(sum(row["costs_brl"][key] for key in
                                         ("spread_cost", "slippage_cost", "fees")),
                                     row["costs_brl"]["total"])
                    if row["final_nav_brl"] is not None:
                        self.assertEqual(row["final_cash_brl"] + row["final_receivable_brl"] +
                                         row["final_positions_value_brl"], row["final_nav_brl"])
                    if strategy == "cash":
                        self.assertEqual((row["orders"], row["fills"], row["costs_brl"]["total"]),
                                         (0, 0, Decimal(0)))
                        self.assertEqual(row["final_nav_brl"], Decimal("100000.00"))
                    else:
                        self.assertEqual(row["complete_series_return"], None)
                        self.assertEqual(row["return_status"], "UNAVAILABLE_INCOMPLETE_NAV")
            self.assertEqual(report["comparisons"]["cash"]["zero_to_base"]["monotonicity"], "PASS")
            self.assertEqual(report["comparisons"]["cash"]["base_to_high"]["monotonicity"], "PASS")
            for strategy in ("momentum", "equal_weight"):
                self.assertEqual([runs[name]["fills"] for name in ("zero", "base", "high")
                                  for runs in [report["runs"][strategy]]], [15, 16, 15])
                for comparison in report["comparisons"][strategy].values():
                    self.assertEqual(comparison["monotonicity"], "NOT_COMPARABLE_EXECUTION_CHANGED")
                    self.assertTrue(comparison["order_differences"])
                    self.assertTrue(comparison["fill_differences"])

    def test_changed_fill_quantity_prevents_monotonicity_claim(self):
        snapshot, decisions = four_cycles()
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "sensitivity"
            run_cost_sensitivity(snapshot, decision_ats=decisions, directory=root)
            comparison = compare_pair(root / "momentum-zero", root / "momentum-high")
            self.assertFalse(comparison["fills_identical"])
            self.assertEqual(comparison["monotonicity"], "NOT_COMPARABLE_EXECUTION_CHANGED")
            self.assertNotIn("complete_nav_nonincreasing", comparison)

    def test_fixed_nonzero_fills_have_nondecreasing_cost_and_nav_drag(self):
        snapshot, decisions = four_cycles()
        with TemporaryDirectory() as tmp:
            roots = []
            for label, spread, slippage, fees in (("zero", 0, 0, 0), ("high", 15, 15, 10)):
                config = replace(F1Config(), max_participation=Decimal("0.0001"),
                                 half_spread_bps=Decimal(spread),
                                 slippage_bps=Decimal(slippage), fees_bps=Decimal(fees))
                result = run_f1_monthly(snapshot, decision_ats=decisions, config=config)
                self.assertGreater(len(result["fills"]), 0)
                roots.append(write_f1_run(snapshot, result, Path(tmp) / label))
            comparison = compare_pair(*roots)
            self.assertTrue(comparison["fills_identical"])
            self.assertEqual(comparison["monotonicity"], "PASS")
            self.assertEqual(comparison["nav_points_compared"], 65)


if __name__ == "__main__":
    unittest.main()
