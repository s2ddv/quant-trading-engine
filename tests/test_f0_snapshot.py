from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qtre.data.snapshot import SnapshotError, load_snapshot, parse_snapshot


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class SnapshotF0Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.normal = json.loads((EXAMPLES / "synthetic_normal_v1.json").read_text())

    def invalid(self, change, match: str) -> None:
        payload = deepcopy(self.normal)
        change(payload)
        with self.assertRaisesRegex(SnapshotError, match):
            parse_snapshot(payload)

    def test_fixtures_are_valid_and_distinct(self) -> None:
        normal = load_snapshot(EXAMPLES / "synthetic_normal_v1.json")
        adverse = load_snapshot(EXAMPLES / "synthetic_adverse_v1.json")
        self.assertEqual(len(normal.payload["bars"]), 6)
        self.assertEqual(len(adverse.payload["bars"]), 5)
        self.assertEqual(len(adverse.payload["actions"]), 2)
        self.assertNotEqual(normal.content_hash, adverse.content_hash)

    def test_hash_is_stable_across_whitespace_and_key_order(self) -> None:
        first = parse_snapshot(self.normal)
        second = parse_snapshot(json.loads(json.dumps(self.normal, sort_keys=False, indent=4)))
        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.content_hash, load_snapshot(EXAMPLES / "synthetic_normal_v1.json").content_hash)
        self.normal["bars"][0]["volume_shares"] += 1
        self.assertNotEqual(first.content_hash, parse_snapshot(self.normal).content_hash)

    def test_snapshot_is_immutable(self) -> None:
        snapshot = parse_snapshot(self.normal)
        with self.assertRaises(TypeError):
            snapshot.payload["bars"][0]["close"] = 0

    def test_as_of_excludes_later_publications(self) -> None:
        snapshot = parse_snapshot(self.normal)
        at_open = datetime(2025, 1, 30, 13, 0, tzinfo=timezone.utc)
        self.assertEqual(len(snapshot.available("opens", at_open)), 2)
        self.assertEqual(len(snapshot.available("bars", at_open)), 0)
        with self.assertRaisesRegex(SnapshotError, "timezone"):
            snapshot.available("bars", datetime(2025, 1, 30, 13, 0))

    def test_rejects_duplicate_bar(self) -> None:
        self.invalid(lambda p: p["bars"].append(deepcopy(p["bars"][0])), "duplicate")

    def test_rejects_duplicate_json_key(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(SnapshotError, "duplicate JSON key"):
                load_snapshot(path)

    def test_rejects_naive_timestamp(self) -> None:
        self.invalid(lambda p: p["bars"][0].update(available_at="2025-01-30T20:05:00"), "timezone")

    def test_rejects_invalid_price(self) -> None:
        self.invalid(lambda p: p["bars"][0].update(close=0), "positive")
        self.invalid(lambda p: p["bars"][0].update(high=9), "OHLC")

    def test_rejects_overlapping_universe(self) -> None:
        self.invalid(lambda p: p["memberships"].append(deepcopy(p["memberships"][0])), "overlapping")

    def test_rejects_future_data(self) -> None:
        self.invalid(lambda p: p["bars"][0].update(available_at="2025-02-05T00:00:00Z"), "future data")

    def test_rejects_complete_bar_at_open(self) -> None:
        def change(p):
            p["bars"][0].update(observed_at="2025-01-30T13:00:00Z", available_at="2025-01-30T13:00:00Z", ingested_at="2025-01-30T13:01:00Z")
        self.invalid(change, "before session close")


if __name__ == "__main__":
    unittest.main()
