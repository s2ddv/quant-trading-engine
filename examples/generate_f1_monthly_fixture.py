"""Extend the controlled synthetic portfolio through a third formation."""

from datetime import date, timedelta
from pathlib import Path

from generate_f1_fixture import provenance, render_snapshot, stamp
from generate_f1_rebalance_fixture import build_rebalance


HERE = Path(__file__).resolve().parent
NAME = "synthetic-f1-monthly-v1"


def build_monthly():
    root = build_rebalance()
    root["snapshot_id"] = NAME
    root["as_of"] = "2025-04-04T00:00:00Z"
    for collection in ("bars", "opens", "actions", "memberships", "symbols"):
        for row in root[collection]:
            row["snapshot_id"] = NAME

    day = date(2025, 3, 6)
    while day <= date(2025, 4, 3):
        if day.weekday() < 5:
            key = day.isoformat()
            root["calendar"]["sessions"].append(
                dict(session=key, open_at=stamp(day, 13), close_at=stamp(day, 20)))
            prices = (25, 31, 32, 33, 20) if day >= date(2025, 3, 31) else (20, 31, 32, 33, 25)
            for index, price in enumerate(prices, 1):
                ident = f"SYN-{index:03d}"
                row_source = dict(provenance(stamp(day, 13), stamp(day, 13), stamp(day, 13, 1)),
                                  snapshot_id=NAME)
                root["opens"].append(dict(instrument_id=ident, session=key, open_price=price,
                                          currency="BRL", tradable=True, **row_source))
                bar_source = dict(provenance(stamp(day, 20), stamp(day, 20, 5), stamp(day, 20, 6)),
                                  snapshot_id=NAME)
                root["bars"].append(dict(instrument_id=ident, session=key, open=price,
                                         high=price + 0.1, low=price - 0.1, close=price,
                                         volume_shares=100000, volume_brl=2000000,
                                         currency="BRL", adjustment_basis="raw", **bar_source))
        day += timedelta(days=1)
    return root


if __name__ == "__main__":
    (HERE / "synthetic_f1_monthly_v1.json").write_text(
        render_snapshot(build_monthly()) + "\n", encoding="utf-8")
