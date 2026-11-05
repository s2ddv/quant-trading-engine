"""Session indexes preserve point-in-time filtering and frozen rows."""

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from qtre.data.snapshot import SnapshotError, parse_snapshot


FIXTURE = Path(__file__).resolve().parents[1] / 'examples/synthetic_f1_monthly_v1.json'


class SessionQueryTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def test_index_matches_full_scan_before_and_after_publication(self):
        self.payload['bars'].reverse()
        self.payload['opens'].reverse()
        snapshot = parse_snapshot(self.payload)
        original_hash = snapshot.content_hash
        for name in ('bars', 'opens'):
            for hour, minute in ((13, 0), (20, 4), (20, 5), (20, 7)):
                cutoff = datetime(2025, 3, 31, hour, minute, tzinfo=timezone.utc)
                known = snapshot.available(name, cutoff)
                for day in ('2025-02-04', '2025-03-31', '2025-04-01', '2099-01-01'):
                    with self.subTest(name=name, cutoff=cutoff, day=day):
                        expected = tuple(r for r in known if r['session'] == day)
                        self.assertEqual(snapshot.available(name, cutoff, session=day), expected)
        self.assertEqual(snapshot.content_hash, original_hash)
        row = snapshot.available('bars', snapshot.as_of, session='2025-03-31')[0]
        with self.assertRaises(TypeError):
            row['close'] = 0

    def test_late_open_is_not_visible_early_even_after_future_query(self):
        event = next(r for r in self.payload['opens']
                     if r['session'] == '2025-04-01' and r['instrument_id'] == 'SYN-003')
        event.update(available_at='2025-04-01T13:01:00Z', ingested_at='2025-04-01T13:02:00Z')
        snapshot = parse_snapshot(self.payload)
        snapshot.available('opens', snapshot.as_of, session='2025-04-01')
        rows = snapshot.available('opens', datetime(2025, 4, 1, 13, tzinfo=timezone.utc),
                                  session='2025-04-01')
        self.assertNotIn('SYN-003', [r['instrument_id'] for r in rows])

    def test_session_filter_still_validates_cutoff_and_collection(self):
        snapshot = parse_snapshot(self.payload)
        with self.assertRaisesRegex(SnapshotError, 'timezone'):
            snapshot.available('bars', datetime(2025, 3, 31), session='missing')
        with self.assertRaisesRegex(SnapshotError, 'later than frozen snapshot'):
            snapshot.available('opens', datetime(2099, 1, 1, tzinfo=timezone.utc), session='missing')
        with self.assertRaisesRegex(SnapshotError, 'session filter'):
            snapshot.available('actions', snapshot.as_of, session='2025-03-31')


if __name__ == '__main__':
    unittest.main()
