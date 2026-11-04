"""Regressions found while reviewing the first F1 implementation."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest

from qtre.data.snapshot import SnapshotError, parse_snapshot
from qtre.signals import momentum_12_2


FIXTURE = Path(__file__).resolve().parents[1] / "examples/synthetic_f1_v1.json"
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class SignalReviewTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def scores(self, payload=None, **kwargs):
        return momentum_12_2(parse_snapshot(payload or self.payload), decision_at=DECISION, **kwargs)

    def test_clock_validation_at_public_entry(self):
        snapshot = parse_snapshot(self.payload)
        for value, message in ((datetime(2025, 1, 31), "timezone"),
                               (datetime(2026, 1, 1, tzinfo=timezone.utc), "later than")):
            with self.subTest(value=value), self.assertRaisesRegex(SnapshotError, message):
                momentum_12_2(snapshot, decision_at=value)

    def test_late_month_end_publication_with_explicit_formation(self):
        bar = next(r for r in self.payload["bars"] if r["instrument_id"] == "SYN-001" and r["session"] == "2025-01-31")
        bar.update(available_at="2025-02-03T21:00:00Z", ingested_at="2025-02-03T21:01:00Z")
        self.assertEqual(self.scores()[0].reason, "missing_monthly_close")
        signals = momentum_12_2(parse_snapshot(self.payload),
                               decision_at=datetime(2025, 2, 3, 21, 2, tzinfo=timezone.utc),
                               formation_session="2025-01-31")
        self.assertEqual(signals[0].score, Decimal("0.2"))
        self.assertEqual(signals[0].input_max_available_at, datetime(2025, 2, 3, 21, tzinfo=timezone.utc))
        self.assertNotIn("bar:SYN-001:2025-02-03", signals[0].input_keys)

    def test_contiguous_membership_rows_preserve_history_but_gaps_do_not(self):
        original = self.scores()[0].score
        first = self.payload["memberships"][0]
        second = dict(first, valid_from="2024-07-01")
        first["valid_to"] = "2024-06-30"
        self.payload["memberships"].append(second)
        self.assertEqual(self.scores()[0].score, original)
        second["valid_from"] = "2024-07-02"
        self.assertEqual(self.scores()[0].reason, "insufficient_membership_history")

    def test_two_dividends_on_same_day_are_added_not_compounded(self):
        template = dict(self.payload["actions"][1], instrument_id="SYN-001", ex_session="2024-12-31",
                        pay_session="2025-01-02", announced_at="2024-12-30T10:00:00Z",
                        observed_at="2024-12-30T10:00:00Z", available_at="2024-12-30T10:01:00Z",
                        ingested_at="2024-12-30T10:02:00Z", cash_per_share=1)
        self.payload["actions"] += [dict(template, action_id="D1"), dict(template, action_id="D2")]
        # 1 share at 10 -> (1 + 2/12) shares at 12: (12 + 2)/10 - 1.
        self.assertAlmostEqual(self.scores()[0].score, Decimal("0.4"), places=25)
        self.payload["actions"].reverse()
        self.assertAlmostEqual(self.scores()[0].score, Decimal("0.4"), places=25)

    def test_split_score_and_missing_ex_price(self):
        event = dict(self.payload["actions"][0], ex_session="2024-12-31",
                     announced_at="2024-12-30T10:00:00Z", observed_at="2024-12-30T10:00:00Z",
                     available_at="2024-12-30T10:01:00Z", ingested_at="2024-12-30T10:02:00Z")
        self.payload["actions"] = [event]
        bar = next(r for r in self.payload["bars"] if r["instrument_id"] == "SYN-001" and r["session"] == "2024-12-31")
        bar.update(open=6, high=6, low=6, close=6)
        self.assertEqual(self.scores()[0].score, Decimal("0.2"))

    def test_zero_volume_days_do_not_count_toward_fifty_valid_sessions(self):
        for bar in self.payload["bars"]:
            if bar["instrument_id"] == "SYN-001" and bar["session"] >= "2025-01-01":
                bar["volume_shares"] = 0
        self.assertEqual(self.scores()[0].reason, "insufficient_liquidity")

    def test_signal_precision_is_independent_of_callers_decimal_context(self):
        expected = self.scores()
        with localcontext() as ctx:
            ctx.prec = 6
            self.assertEqual(expected, self.scores())

    def test_parser_rejects_impossible_action_and_open_clocks(self):
        for mutate, pattern in (
            (lambda p: p["actions"][1].update(pay_session="2025-02-03"), "before ex_session"),
            (lambda p: p["actions"][1].update(ex_session=None), "not in calendar"),
            (lambda p: p["opens"][0].update(observed_at="2024-01-01T00:00:00Z"), "observed before"),
        ):
            payload = deepcopy(self.payload)
            mutate(payload)
            with self.subTest(pattern=pattern), self.assertRaisesRegex(SnapshotError, pattern):
                parse_snapshot(payload)
