"""Extend the controlled F1 fixture through a second monthly formation."""

from datetime import date, timedelta
from pathlib import Path

from generate_f1_fixture import build, provenance, render_snapshot, stamp


HERE = Path(__file__).resolve().parent
NAME = "synthetic-f1-rebalance-v1"


def _provenance(observed, available, ingested):
    return dict(provenance(observed, available, ingested), snapshot_id=NAME)


def build_rebalance():
    root = build()
    root["snapshot_id"] = NAME
    root["as_of"] = "2025-03-06T00:00:00Z"
    for collection in ("bars", "opens", "actions", "memberships", "symbols"):
        for row in root[collection]:
            row["snapshot_id"] = NAME

    day = date(2025, 2, 6)
    while day <= date(2025, 3, 5):
        if day.weekday() < 5:
            key = day.isoformat()
            root["calendar"]["sessions"].append(dict(session=key, open_at=stamp(day, 13), close_at=stamp(day, 20)))
            for index in range(1, 6):
                ident = f"SYN-{index:03d}"
                if day >= date(2025, 2, 28):
                    price = (20, 31, 32, 33, 25)[index - 1]
                else:
                    price = (15, 31, 32, 33, 34)[index - 1]
                root["opens"].append(dict(instrument_id=ident, session=key, open_price=price,
                                          currency="BRL", tradable=True,
                                          **_provenance(stamp(day, 13), stamp(day, 13), stamp(day, 13, 1))))
                root["bars"].append(dict(instrument_id=ident, session=key,
                                         open=price, high=price + 0.1, low=price - 0.1,
                                         close=price, volume_shares=100000, volume_brl=2000000,
                                         currency="BRL", adjustment_basis="raw",
                                         **_provenance(stamp(day, 20), stamp(day, 20, 5), stamp(day, 20, 6))))
        day += timedelta(days=1)
    return root


if __name__ == "__main__":
    (HERE / "synthetic_f1_rebalance_v1.json").write_text(render_snapshot(build_rebalance()) + "\n", encoding="utf-8")
