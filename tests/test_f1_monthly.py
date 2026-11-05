"""Third synthetic decision, dated exits, and independent replay."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from qtre.backtest import run_f1_monthly, run_f1_two_formations
from qtre.backtest.rebalance import _sell_quote
from qtre.backtest import F1Config
from qtre.data.snapshot import SnapshotError, load_snapshot, parse_snapshot
from qtre.reporting import ReplayError, replay_f1, write_f1_run


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_monthly_v1.json"
DECISIONS = tuple(datetime(2025, month, day, 20, 7, tzinfo=timezone.utc)
                  for month, day in ((1, 31), (2, 28), (3, 31)))


class MonthlyTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def run_case(self):
        return run_f1_monthly(parse_snapshot(self.payload), decision_ats=DECISIONS)

    def test_third_formation_matches_manual_costs_and_nav(self):
        result = self.run_case()
        orders = [(row["instrument_id"], row["side"], row["quantity"])
                  for row in result["orders"] if row["order_id"].startswith("O3-")]
        self.assertEqual(orders, [("SYN-001", "sell", 98), ("SYN-002", "buy", 1),
                                  ("SYN-003", "buy", 2), ("SYN-004", "buy", 1),
                                  ("SYN-005", "buy", 103)])
        formation = next(row for row in result["nav"] if row["session"] == "2025-03-31")
        executed = next(row for row in result["nav"] if row["session"] == "2025-04-01")
        self.assertEqual((formation["cash_brl"], formation["positions_value_brl"], formation["nav_brl"]),
                         (Decimal("50432.20"), Decimal("50823.00"), Decimal("101255.20")))
        self.assertEqual((executed["cash_brl"], executed["positions_value_brl"], executed["nav_brl"]),
                         (Decimal("50687.25"), Decimal("50561.00"), Decimal("101248.25")))
        fills = [row for row in result["fills"] if row["order_id"].startswith("O3-")]
        self.assertEqual(fills[0]["cash_credit"], Decimal("2446.33"))
        self.assertEqual((fills[0]["basis_removed"], fills[0]["realized_pnl"]),
                         (Decimal("1472.21"), Decimal("974.12")))
        self.assertEqual([row["cash_debit"] for row in fills[1:]],
                         list(map(Decimal, ("31.05", "64.09", "33.05", "2063.09"))))
        self.assertEqual(sum(row["spread_cost"] + row["slippage_cost"] + row["fees"]
                             for row in fills), Decimal("6.95"))

    def test_third_run_replays_deterministically_without_engine(self):
        snapshot = load_snapshot(FIXTURE)
        result = run_f1_monthly(snapshot, decision_ats=DECISIONS)
        with TemporaryDirectory() as tmp:
            first = write_f1_run(snapshot, result, Path(tmp) / "first")
            second = write_f1_run(snapshot, result, Path(tmp) / "second")
            for name in first.iterdir():
                self.assertEqual(name.read_bytes(), (second / name.name).read_bytes())
            self.assertEqual(json.loads((first / "manifest.json").read_text())["artifact_schema_version"], 4)
            with patch("qtre.backtest.run_f1", side_effect=AssertionError("engine called")):
                rebuilt = replay_f1(first)
        self.assertEqual(rebuilt["cash_brl"], Decimal("50687.25"))
        self.assertEqual(rebuilt["positions"], {"SYN-001": 405, "SYN-002": 326,
                                                 "SYN-003": 316, "SYN-004": 306,
                                                 "SYN-005": 506})
        self.assertEqual(rebuilt["cost_basis"]["SYN-001"], Decimal("6084.11"))

    def test_two_decision_api_keeps_previous_schema(self):
        snapshot = parse_snapshot(self.payload)
        old_api = run_f1_two_formations(snapshot, first_decision_at=DECISIONS[0],
                                        second_decision_at=DECISIONS[1])
        new_api = run_f1_monthly(snapshot, decision_ats=DECISIONS[:2])
        self.assertEqual(old_api, new_api)
        self.assertEqual(old_api["manifest"]["schema_version"], 4)

    def test_future_open_does_not_rewrite_third_orders(self):
        before = self.run_case()
        for row in self.payload["opens"]:
            if row["session"] >= "2025-04-01":
                row["open_price"] = 100000
        after = self.run_case()
        self.assertEqual(before["orders"], after["orders"])
        self.assertNotEqual(before["fills"], after["fills"])

    def test_third_sale_respects_partial_capacity(self):
        for row in self.payload["bars"]:
            if row["instrument_id"] == "SYN-001" and "2025-03-06" <= row["session"] <= "2025-03-31":
                row["volume_shares"] = 1000
        result = self.run_case()
        sale = [row["quantity"] for row in result["fills"] if row["order_id"] == "O3-SYN-001"]
        self.assertEqual(sale, [50, 48])
        self.assertEqual(result["nav"][-1]["status"], "COMPLETE")

    def test_suspended_third_sale_cannot_fund_new_buys(self):
        config = F1Config(max_name_weight=Decimal("0.20"))
        for row in self.payload["opens"]:
            if row["instrument_id"] == "SYN-001" and row["session"] >= "2025-04-01":
                row["tradable"] = False
        result = run_f1_monthly(parse_snapshot(self.payload), decision_ats=DECISIONS, config=config)
        formation = next(row for row in result["nav"] if row["session"] == "2025-03-31")
        fills = [row for row in result["fills"] if row["order_id"].startswith("O3-")]
        self.assertEqual(formation["cash_brl"], Decimal("23.09"))
        self.assertFalse(any(row["side"] == "sell" for row in fills))
        self.assertLessEqual(sum((row["cash_debit"] for row in fills), Decimal(0)),
                             formation["cash_brl"])
        self.assertTrue(any(row["order_id"] == "O3-SYN-001" and row["status"] == "EXPIRED"
                            for row in result["order_states"]))

    def test_third_orders_and_fills_obey_configured_lot(self):
        result = run_f1_monthly(parse_snapshot(self.payload), decision_ats=DECISIONS,
                                config=F1Config(lot=10))
        self.assertTrue(all(row["quantity"] % 10 == 0 for row in result["orders"]
                            if row["order_id"].startswith("O3-")))
        self.assertTrue(all(row["quantity"] % 10 == 0 for row in result["fills"]
                            if row["order_id"].startswith("O3-")))

    def test_total_sale_removes_exact_cost_basis(self):
        quote = _sell_quote(Decimal("10"), 3, F1Config(), 3, Decimal("100.01"))
        self.assertEqual(quote["basis_removed"], Decimal("100.01"))
        self.assertEqual(Decimal("100.01") - quote["basis_removed"], Decimal(0))

    def extend_to_fourth(self):
        last_bars = {row["instrument_id"]: row for row in self.payload["bars"]
                     if row["session"] == "2025-04-03"}
        last_opens = {row["instrument_id"]: row for row in self.payload["opens"]
                      if row["session"] == "2025-04-03"}
        day = date(2025, 4, 4)
        while day <= date(2025, 5, 5):
            if day.weekday() < 5:
                key = day.isoformat()
                self.payload["calendar"]["sessions"].append(
                    {"session": key, "open_at": f"{key}T13:00:00Z", "close_at": f"{key}T20:00:00Z"})
                for ident in last_bars:
                    opening = dict(last_opens[ident], session=key,
                                   observed_at=f"{key}T13:00:00Z", available_at=f"{key}T13:00:00Z",
                                   ingested_at=f"{key}T13:01:00Z")
                    bar = dict(last_bars[ident], session=key, observed_at=f"{key}T20:00:00Z",
                               available_at=f"{key}T20:05:00Z", ingested_at=f"{key}T20:06:00Z")
                    self.payload["opens"].append(opening)
                    self.payload["bars"].append(bar)
            day += timedelta(days=1)
        self.payload["as_of"] = "2025-05-06T00:00:00Z"
        return DECISIONS + (datetime(2025, 4, 30, 20, 7, tzinfo=timezone.utc),)

    def test_fourth_decision_repeats_cycle_and_replays(self):
        decisions = self.extend_to_fourth()
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=decisions)
        self.assertEqual(len(result["manifest"]["decision_windows"]), 4)
        self.assertTrue(any(row["order_id"].startswith("O4-") for row in result["orders"]))
        with TemporaryDirectory() as tmp:
            rebuilt = replay_f1(write_f1_run(snapshot, result, Path(tmp) / "four-cycles"))
        self.assertEqual(rebuilt["nav"][-1]["session"], "2025-05-05")
        self.assertEqual(rebuilt["cash_brl"], result["nav"][-1]["cash_brl"])

    def test_fewer_than_five_eligible_liquidates_full_positions(self):
        decisions = self.extend_to_fourth()
        for bar in self.payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and bar["session"].startswith("2025-04"):
                bar["volume_brl"] = 0
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=decisions)
        self.assertEqual(result["manifest"]["decision_windows"][-1]["portfolio_reason"],
                         "fewer_than_five_eligible")
        orders = [row for row in result["orders"] if row["order_id"].startswith("O4-")]
        self.assertEqual(len(orders), 5)
        self.assertTrue(all(row["side"] == "sell" for row in orders))
        marks = next(nav for nav in result["nav"] if nav["session"] == "2025-04-30")["marks"]
        self.assertTrue(all(row["quantity"] == marks[row["instrument_id"]]["quantity"] for row in orders))
        with TemporaryDirectory() as tmp:
            rebuilt = replay_f1(write_f1_run(snapshot, result, Path(tmp) / "cash-fallback"))
        self.assertTrue(all(quantity == 0 for quantity in rebuilt["positions"].values()))
        self.assertEqual(rebuilt["nav"][-1]["positions_value_brl"], "0.00")

    def test_unresolved_delisting_keeps_position_and_incomplete_nav(self):
        original = next(row for row in self.payload["memberships"] if row["instrument_id"] == "SYN-001")
        original["valid_to"] = "2025-04-01"
        delisted = dict(original, valid_from="2025-04-02", valid_to=None, status="delisted",
                        reason="synthetic delisting", observed_at="2025-04-01T18:00:00Z",
                        available_at="2025-04-01T18:01:00Z", ingested_at="2025-04-01T18:02:00Z")
        self.payload["memberships"].append(delisted)
        action = dict(self.payload["actions"][0], action_id="SYN-DELIST", kind="delisting",
                      ex_session="2025-04-02", observed_at="2025-04-01T18:00:00Z",
                      announced_at="2025-04-01T18:00:00Z", available_at="2025-04-01T18:01:00Z",
                      ingested_at="2025-04-01T18:02:00Z")
        action.pop("ratio")
        self.payload["actions"].append(action)
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=DECISIONS)
        last = result["nav"][-1]
        self.assertEqual((last["status"], last["missing_marks"], last["nav_brl"]),
                         ("NAV_INCOMPLETO", ["SYN-001"], None))
        self.assertFalse(any(row["side"] == "sell" and row["session"] >= "2025-04-02"
                             for row in result["fills"] if "side" in row))
        with TemporaryDirectory() as tmp:
            path = write_f1_run(snapshot, result, Path(tmp) / "delisted")
            rebuilt = replay_f1(path)
            ledger_path = path / "ledger.jsonl"
            ledger_path.write_text("".join(line + "\n" for line in ledger_path.read_text().splitlines()
                                           if json.loads(line)["event_id"] != "SYN-DELIST"))
            manifest_path = path / "manifest.json"
            envelope = json.loads(manifest_path.read_text())
            envelope["files"]["ledger.jsonl"] = sha256(ledger_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n")
            with self.assertRaisesRegex(ReplayError, "missing corporate action SYN-DELIST"):
                replay_f1(path)
        self.assertEqual(rebuilt["positions"]["SYN-001"], 405)
        self.assertEqual(rebuilt["nav"][-1]["status"], "NAV_INCOMPLETO")

    def test_known_delisting_cash_replaces_position_then_settles(self):
        original = next(row for row in self.payload["memberships"] if row["instrument_id"] == "SYN-001")
        original["valid_to"] = "2025-04-01"
        self.payload["memberships"].append(dict(
            original, valid_from="2025-04-02", valid_to=None, status="delisted",
            reason="synthetic cash settlement", observed_at="2025-04-01T18:00:00Z",
            available_at="2025-04-01T18:01:00Z", ingested_at="2025-04-01T18:02:00Z"))
        action = dict(self.payload["actions"][0], action_id="SYN-CASH-EXIT", kind="delisting",
                      ex_session="2025-04-02", pay_session="2025-04-03",
                      exit_cash_per_share=26, observed_at="2025-04-01T18:00:00Z",
                      announced_at="2025-04-01T18:00:00Z", available_at="2025-04-01T18:01:00Z",
                      ingested_at="2025-04-01T18:02:00Z")
        action.pop("ratio")
        self.payload["actions"].append(action)
        with self.assertRaisesRegex(SnapshotError, "unknown"):
            parse_snapshot(self.payload)
        self.payload["schema_version"] = 2
        action["exit_cash_per_share"] = -1
        with self.assertRaisesRegex(SnapshotError, "non-negative"):
            parse_snapshot(self.payload)
        action["exit_cash_per_share"] = 26
        action.pop("pay_session")
        with self.assertRaisesRegex(SnapshotError, "requires payment"):
            parse_snapshot(self.payload)
        action["pay_session"] = "2025-04-03"
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=DECISIONS)
        ex = next(row for row in result["nav"] if row["session"] == "2025-04-02")
        paid = next(row for row in result["nav"] if row["session"] == "2025-04-03")
        self.assertEqual((ex["cash_brl"], ex["receivable_brl"], ex["positions_value_brl"], ex["nav_brl"]),
                         (Decimal("50687.25"), Decimal("10530.00"), Decimal("40436.00"),
                          Decimal("101653.25")))
        self.assertEqual((paid["cash_brl"], paid["receivable_brl"], paid["nav_brl"]),
                         (Decimal("61217.25"), Decimal(0), Decimal("101653.25")))
        exit_event = next(row for row in result["ledger"] if row["event_id"] == "SYN-CASH-EXIT")
        self.assertEqual((exit_event["quantity"], exit_event["basis_removed"], exit_event["realized_pnl"]),
                         (0, Decimal("6084.11"), Decimal("4445.89")))
        self.assertFalse(any(row["side"] == "sell" and row["session"] >= "2025-04-02"
                             for row in result["fills"] if "side" in row))
        with TemporaryDirectory() as tmp:
            path = write_f1_run(snapshot, result, Path(tmp) / "known-exit")
            self.assertEqual(json.loads((path / "manifest.json").read_text())["artifact_schema_version"], 5)
            rebuilt = replay_f1(path)
            self.assertEqual(rebuilt["cash_brl"], Decimal("61217.25"))
            self.assertEqual(rebuilt["positions"]["SYN-001"], 0)
            self.assertEqual(rebuilt["cost_basis"]["SYN-001"], Decimal(0))
            ledger_path = path / "ledger.jsonl"
            rows = [json.loads(line) for line in ledger_path.read_text().splitlines()]
            next(row for row in rows if row["event_id"] == "SYN-CASH-EXIT")["basis_removed"] = "1.00"
            ledger_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                                           for row in rows))
            manifest_path = path / "manifest.json"
            envelope = json.loads(manifest_path.read_text())
            envelope["files"]["ledger.jsonl"] = sha256(ledger_path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n")
            with self.assertRaisesRegex(ReplayError, "delisting basis removed"):
                replay_f1(path)


if __name__ == "__main__":
    unittest.main()
