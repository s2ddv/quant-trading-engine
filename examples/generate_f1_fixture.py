"""Build a deterministic, wholly synthetic F1 clock and price history."""

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
NAME = "synthetic-f1-v1"


def stamp(day, hour, minute=0):
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}:00Z"


def provenance(observed, available, ingested):
    return dict(source_id="synthetic-fixture", source_version="1", snapshot_id=NAME,
                observed_at=observed, available_at=available, ingested_at=ingested)


def build():
    days = []
    day = date(2024, 1, 1)
    while day <= date(2025, 2, 5):
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    month_ends = {}
    for day in days:
        month_ends[(day.year, day.month)] = day
    recent = {day for day in days if date(2024, 10, 1) <= day <= date(2025, 2, 5)}
    observed_days = sorted(set(month_ends.values()) | recent)
    root = dict(schema_version=1, snapshot_id=NAME, as_of="2025-02-06T00:00:00Z",
                calendar=dict(calendar_id="synthetic-f1-calendar", timezone="America/Sao_Paulo",
                              sessions=[dict(session=d.isoformat(), open_at=stamp(d, 13), close_at=stamp(d, 20)) for d in days]),
                bars=[], opens=[], actions=[], memberships=[], symbols=[])
    initial = date(2024, 1, 1)
    for index in range(1, 6):
        instrument = f"SYN-{index:03d}"
        p = provenance(stamp(initial, 0), stamp(initial, 0, 1), stamp(initial, 0, 2))
        root["memberships"].append(dict(instrument_id=instrument, valid_from=initial.isoformat(), valid_to=None,
                                         status="listed", reason="synthetic", **p))
        root["symbols"].append(dict(instrument_id=instrument, ticker=f"SYN{index}",
                                     valid_from=initial.isoformat(), valid_to=None, **p))
        for d in observed_days:
            # The first name has a hand-checkable 20% score. The others differ in rank.
            if d.year == 2024 and d.month == 1:
                close = 10.0 + index - 1
            elif d.year == 2024 and d.month == 12:
                close = 12.0 + index - 1
            elif d.year == 2025 and d.month == 1:
                close = 30.0 + index - 1
            elif d == date(2025, 2, 3):
                close = 30.0 + index - 1
            elif d >= date(2025, 2, 4):
                close = (30.0 + index - 1) / (2 if index == 1 else 1)
            else:
                close = round(10.0 + index - 1 + (d - initial).days / 400, 2)
            if index == 1 and d.year == 2024 and d.month == 1:
                close = 10.0
            if index == 1 and d.year == 2024 and d.month == 12:
                close = 12.0
            # Missing post-decision mark and suspended opening are deliberate.
            if index == 5 and d == date(2025, 2, 4):
                continue
            tradable = not (index == 4 and d == date(2025, 2, 3))
            opening = close
            root["opens"].append(dict(instrument_id=instrument, session=d.isoformat(), open_price=opening,
                                      currency="BRL", tradable=tradable,
                                      **provenance(stamp(d, 13), stamp(d, 13), stamp(d, 13, 1))))
            if not tradable:
                continue
            root["bars"].append(dict(instrument_id=instrument, session=d.isoformat(), open=opening,
                                     high=round(close + 0.1, 2), low=round(close - 0.1, 2), close=close,
                                     volume_shares=100000, volume_brl=2000000,
                                     currency="BRL", adjustment_basis="raw",
                                     **provenance(stamp(d, 20), stamp(d, 20, 5), stamp(d, 20, 6))))
    # Events occur after the formation date, so they test the event pipeline without
    # changing the hand-calculated first signal.
    for action_id, instrument, kind, extra in (
        ("SYN-SPLIT", "SYN-001", "split", dict(ratio=2)),
        ("SYN-DIV", "SYN-002", "dividend", dict(cash_per_share=0.5, pay_session="2025-02-05")),
    ):
        d = date(2025, 2, 4)
        root["actions"].append(dict(action_id=action_id, instrument_id=instrument, kind=kind,
                                    announced_at=stamp(date(2025, 2, 3), 18), ex_session=d.isoformat(), **extra,
                                    **provenance(stamp(date(2025, 2, 3), 18),
                                                 stamp(date(2025, 2, 3), 18, 1),
                                                 stamp(date(2025, 2, 3), 18, 2))))
    return root


if __name__ == "__main__":
    (HERE / "synthetic_f1_v1.json").write_text(json.dumps(build(), sort_keys=True, indent=2) + "\n")
