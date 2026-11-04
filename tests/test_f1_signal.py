from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import unittest

from qtre.data.snapshot import load_snapshot, parse_snapshot
from qtre.signals import momentum_12_2
from qtre.universe import listed_members


FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_f1_v1.json"
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class F1SignalTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def test_manual_score_and_fixture_extent(self):
        snapshot = parse_snapshot(self.payload)
        self.assertEqual(len({r["session"][:7] for r in snapshot.payload["calendar"]["sessions"]}), 14)
        signals = momentum_12_2(snapshot, decision_at=DECISION)
        self.assertEqual(len(signals), 5)
        self.assertEqual(signals[0].score, Decimal("0.2"))
        self.assertEqual(signals[0].feature_end_session, "2024-12-31")
        self.assertTrue(all(s.input_max_available_at <= DECISION for s in signals))

    def test_future_price_cannot_change_signal(self):
        before = momentum_12_2(parse_snapshot(self.payload), decision_at=DECISION)
        changed = deepcopy(self.payload)
        for bar in changed["bars"]:
            if bar["session"].startswith("2025-02"):
                bar["open"] = bar["high"] = bar["low"] = bar["close"] = 999
        after = momentum_12_2(parse_snapshot(changed), decision_at=DECISION)
        self.assertEqual(before, after)

    def test_excluded_month_jump_does_not_change_score(self):
        before = momentum_12_2(parse_snapshot(self.payload), decision_at=DECISION)[0].score
        changed = deepcopy(self.payload)
        for bar in changed["bars"]:
            if bar["instrument_id"] == "SYN-001" and bar["session"] == "2025-01-31":
                bar["open"] = bar["high"] = bar["low"] = bar["close"] = 300
        after = momentum_12_2(parse_snapshot(changed), decision_at=DECISION)[0].score
        self.assertEqual(before, after)

    def test_late_membership_is_invisible(self):
        changed = deepcopy(self.payload)
        member = changed["memberships"][0]
        member["available_at"] = "2025-02-01T00:00:00Z"
        member["ingested_at"] = "2025-02-01T00:01:00Z"
        snapshot = parse_snapshot(changed)
        self.assertNotIn(member["instrument_id"], listed_members(snapshot, "2025-01-31", as_of=DECISION))


if __name__ == "__main__":
    unittest.main()
