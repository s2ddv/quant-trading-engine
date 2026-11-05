"""Regressions for carrying the book through monthly boundaries."""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qtre.backtest import run_f1, run_f1_monthly
from qtre.data.snapshot import parse_snapshot
from qtre.reporting import replay_f1, write_f1_run


FIXTURE = Path(__file__).resolve().parents[1] / 'examples/synthetic_f1_monthly_v1.json'
DECISIONS = tuple(datetime(2025, month, day, 20, 7, tzinfo=timezone.utc)
                  for month, day in ((1, 31), (2, 28), (3, 31)))


class MonthlyReviewTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE.read_text())

    def add_exit(self, ex_day, pay_day):
        self.payload['schema_version'] = 2
        action = dict(self.payload['actions'][0], action_id='EXIT', kind='delisting',
                      ex_session=ex_day, pay_session=pay_day, exit_cash_per_share=26)
        action.pop('ratio')
        self.payload['actions'].append(action)
        original = next(r for r in self.payload['memberships'] if r['instrument_id'] == 'SYN-001')
        original['valid_to'] = '2025-02-03'
        self.payload['memberships'].append(dict(original, valid_from=ex_day,
                                                valid_to=None, status='delisted'))

    def replay(self, snapshot, result):
        with TemporaryDirectory() as tmp:
            return replay_f1(write_f1_run(snapshot, result, Path(tmp) / 'run'))

    def test_unpaid_exit_survives_multiple_months_and_pays_once(self):
        self.add_exit('2025-02-04', '2025-04-02')
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=DECISIONS)
        # Split before the exit: 329 * 2 * 26 = 17,108 due, no early cash.
        for day in ('2025-02-05', '2025-02-28', '2025-03-31', '2025-04-01'):
            nav = next(r for r in result['nav'] if r['session'] == day)
            self.assertEqual(nav['receivable_brl'], Decimal('17108.00'))
        payments = [r for r in result['ledger'] if r['event_id'] == 'EXIT-pay']
        self.assertEqual(len(payments), 1)
        self.assertEqual((payments[0]['session'], payments[0]['cash_delta']),
                         ('2025-04-02', Decimal('17108.00')))
        self.assertEqual(self.replay(snapshot, result)['receivables'], {})

    def test_exit_in_single_formation_replays_without_zero_quantity_mark(self):
        self.add_exit('2025-02-04', '2025-02-05')
        snapshot = parse_snapshot(self.payload)
        result = run_f1(snapshot, decision_at=DECISIONS[0])
        self.assertNotIn('SYN-001', result['nav'][-1]['marks'])
        rebuilt = self.replay(snapshot, result)
        self.assertEqual(rebuilt['positions']['SYN-001'], 0)
        self.assertEqual(rebuilt['cash_brl'], result['nav'][-1]['cash_brl'])

    def test_missing_last_execution_mark_can_recover_before_next_decision(self):
        self.payload['bars'] = [r for r in self.payload['bars']
                                if (r['instrument_id'], r['session']) != ('SYN-003', '2025-02-05')]
        snapshot = parse_snapshot(self.payload)
        result = run_f1_monthly(snapshot, decision_ats=DECISIONS)
        self.assertEqual(result['nav'][2]['status'], 'NAV_INCOMPLETO')
        self.assertEqual(result['nav'][3]['status'], 'COMPLETE')
        self.assertEqual(self.replay(snapshot, result)['cash_brl'], result['nav'][-1]['cash_brl'])

    def test_unresolved_exit_still_blocks_next_decision(self):
        self.add_exit('2025-02-04', '2025-04-02')
        self.payload['actions'][-1].pop('exit_cash_per_share')
        self.payload['actions'][-1].pop('pay_session')
        with self.assertRaisesRegex(ValueError, 'monthly formation has incomplete NAV'):
            run_f1_monthly(parse_snapshot(self.payload), decision_ats=DECISIONS)

    def test_late_action_crossing_execution_boundary_is_rejected(self):
        late = dict(self.payload['actions'][0], action_id='LATE-BOUNDARY',
                    ex_session='2025-02-05', announced_at='2025-02-06T12:00:00Z',
                    observed_at='2025-02-06T12:00:00Z', available_at='2025-02-06T12:01:00Z',
                    ingested_at='2025-02-06T12:02:00Z')
        self.payload['actions'].append(late)
        with self.assertRaisesRegex(ValueError, 'late corporate action LATE-BOUNDARY'):
            run_f1_monthly(parse_snapshot(self.payload), decision_ats=DECISIONS)


if __name__ == '__main__':
    unittest.main()
