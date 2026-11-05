"""Semantic replay checks after artifact hashes have been recomputed."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qtre.backtest import run_f1
from qtre.data.snapshot import load_snapshot, parse_snapshot
from qtre.reporting import ReplayError, replay_f1, write_f1_run


FIXTURE = Path(__file__).resolve().parents[1] / 'examples/synthetic_f1_v1.json'
DECISION = datetime(2025, 1, 31, 20, 7, tzinfo=timezone.utc)


class ReplayReviewTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_snapshot(FIXTURE)
        self.result = run_f1(self.snapshot, decision_at=DECISION)

    def replay(self, result):
        with TemporaryDirectory() as tmp:
            return replay_f1(write_f1_run(self.snapshot, result, Path(tmp) / 'run'))

    def test_order_cannot_be_overfilled_with_negative_remaining(self):
        result = deepcopy(self.result)
        result['orders'][0]['quantity'] -= 1
        result['order_states'][0].update(remaining=-1, status='EXPIRED')
        with self.assertRaisesRegex(ReplayError, 'exceeds order quantity'):
            self.replay(result)

    def test_fully_filled_order_cannot_be_marked_expired_or_cancelled(self):
        for status in ('EXPIRED', 'CANCELLED'):
            with self.subTest(status=status):
                result = deepcopy(self.result)
                result['order_states'][0]['status'] = status
                with self.assertRaisesRegex(ReplayError, 'terminal order status'):
                    self.replay(result)

    def test_fabricated_cancellation_without_action_is_rejected(self):
        payload = json.loads(FIXTURE.read_text())
        payload['opens'] = [r for r in payload['opens'] if r['instrument_id'] != 'SYN-003']
        self.snapshot = parse_snapshot(payload)
        result = run_f1(self.snapshot, decision_at=DECISION)
        state = next(s for s in result['order_states'] if s['instrument_id'] == 'SYN-003')
        state.update(status='CANCELLED', reason='split_requires_new_order')
        with self.assertRaisesRegex(ReplayError, 'terminal order status'):
            self.replay(result)

    def test_split_cancellation_replays_and_cannot_be_erased(self):
        payload = json.loads(FIXTURE.read_text())
        for bar in payload['bars']:
            if bar['instrument_id'] == 'SYN-001' and bar['session'] <= '2025-01-31':
                bar['volume_shares'] = 1000
        self.snapshot = parse_snapshot(payload)
        result = run_f1(self.snapshot, decision_at=DECISION)
        self.assertEqual(self.replay(result)['positions']['SYN-001'], 100)
        state = next(s for s in result['order_states'] if s['instrument_id'] == 'SYN-001')
        state.update(status='EXPIRED', reason='expiry_session_reached')
        with self.assertRaisesRegex(ReplayError, 'terminal order status'):
            self.replay(result)

    def test_action_cannot_be_moved_after_same_day_trading(self):
        result = deepcopy(self.result)
        ledger = list(result['ledger'])
        split = next(r for r in ledger if r['kind'] == 'split')
        ledger.remove(split)
        last_index = max(i for i, r in enumerate(ledger) if r['session'] == split['session'])
        split.update(cash_brl=ledger[last_index]['cash_brl'],
                     receivable_brl=ledger[last_index]['receivable_brl'])
        ledger.insert(last_index + 1, split)
        result['ledger'] = tuple(ledger)
        with self.assertRaisesRegex(ReplayError, 'corporate action recorded after trading'):
            self.replay(result)

    def test_payment_cannot_name_another_instrument(self):
        result = deepcopy(self.result)
        payment = next(r for r in result['ledger'] if r['kind'] == 'dividend_pay')
        # Reconcile the other position too, so identity is the only mismatch.
        other = next(r for r in reversed(result['ledger']) if r['instrument_id'] == 'SYN-003')
        payment.update(instrument_id='SYN-003', quantity=other['quantity'], cost_basis=other['cost_basis'])
        with self.assertRaisesRegex(ReplayError, 'payment identity'):
            self.replay(result)


if __name__ == '__main__':
    unittest.main()
