"""Bounded generated checks for existing accounting and temporal contracts."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from hypothesis import given, settings, strategies as st

from qtre.backtest import F1Config, _affordable_fill
from qtre.data.snapshot import load_snapshot

FIXTURE = Path(__file__).resolve().parents[2] / "examples/synthetic_normal_v1.json"
BOUNDED = settings(max_examples=40, derandomize=True, database=None, deadline=None)


@BOUNDED
@given(
    price_cents=st.integers(1, 100000),
    cash_cents=st.integers(0, 1000000),
    maximum=st.integers(0, 100),
    lot=st.integers(1, 20),
)
def test_affordable_lot_matches_exhaustive_decimal_oracle(price_cents, cash_cents, maximum, lot):
    price = Decimal(price_cents) / 100
    cash = Decimal(cash_cents) / 100
    config = F1Config(lot=lot)

    # Default model: 5 bps spread + 5 bps slippage, then 5 bps fee.
    # Enumerate all legal quantities independently of the engine's binary search.
    def debit(quantity):
        notional = (price * quantity * Decimal("1.001")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        fee = (notional * Decimal("0.0005")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return notional + fee

    expected = max(q for q in range(0, maximum + 1, lot) if debit(q) <= cash)
    actual = _affordable_fill(price, maximum, cash, config)
    assert actual == expected
    assert actual % lot == 0
    assert debit(actual) <= cash


@BOUNDED
@given(first=st.integers(0, 2800), second=st.integers(0, 2800))
def test_availability_is_monotone_and_future_cache_cannot_leak(first, second):
    snapshot = load_snapshot(FIXTURE)
    start = datetime(2025, 1, 30, tzinfo=timezone.utc)
    early, late = sorted((start + timedelta(minutes=first), start + timedelta(minutes=second)))
    for collection in ("bars", "opens"):
        # Populate the session cache from the future, then ask historical questions.
        snapshot.available(collection, snapshot.as_of, session="2025-01-30")
        before = snapshot.available(collection, early)
        after = snapshot.available(collection, late)
        assert all(row in after for row in before)
        assert all(
            datetime.fromisoformat(row["available_at"].replace("Z", "+00:00")) <= early
            for row in before
        )
        assert snapshot.available(collection, early, session="2025-01-30") == tuple(
            row for row in before if row["session"] == "2025-01-30"
        )
