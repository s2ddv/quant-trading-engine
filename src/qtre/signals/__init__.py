"""Point-in-time research signals."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Context, Decimal, localcontext
from itertools import groupby
from statistics import median

from qtre.data.snapshot import Snapshot
from qtre.calendar import formation_sessions
from qtre.universe import listed_members


@dataclass(frozen=True)
class Signal:
    instrument_id: str
    decision_at: datetime
    feature_end_session: str
    input_max_available_at: datetime | None
    score: Decimal | None
    eligible: bool
    reason: str
    input_keys: tuple[str, ...] = ()


def momentum_12_2(snapshot: Snapshot, *, decision_at: datetime,
                  formation_session: str | None = None) -> tuple[Signal, ...]:
    """Score the next execution month using 13 consecutive monthly closes."""
    with localcontext(Context(prec=28)):
        return _momentum_12_2(snapshot, decision_at, formation_session)


def _momentum_12_2(snapshot, decision_at, formation_session):
    past = formation_sessions(snapshot, decision_at, formation_session)
    formation = past[-1]["session"]
    months: dict[str, str] = {}
    for row in past:
        months[row["session"][:7]] = row["session"]
    keys = sorted(months)
    if len(keys) < 13:
        raise ValueError("decision requires 13 completed months at a month end")
    window = [months[key] for key in keys[-13:]]
    # Consecutive calendar months are required, even if a snapshot omits one.
    for left, right in zip(keys[-13:], keys[-12:]):
        year, month = map(int, left.split("-"))
        expected = f"{year + (month == 12):04d}-{month % 12 + 1:02d}"
        if right != expected:
            raise ValueError("monthly history has a calendar gap")
    bars = {(r["instrument_id"], r["session"]): r for r in snapshot.available("bars", decision_at)}
    actions = snapshot.available("actions", decision_at)
    memberships = listed_members(snapshot, formation, as_of=decision_at)
    known_memberships = snapshot.available("memberships", decision_at)
    recent_sessions = [r["session"] for r in past[-63:]]
    results = []
    for instrument in memberships:
        used = []
        def finish(score, reason):
            latest = max((datetime.fromisoformat(r["available_at"].replace("Z", "+00:00")) for r in used), default=None)
            input_keys = tuple(sorted({
                (f"action:{r['action_id']}" if "action_id" in r else
                 f"bar:{instrument}:{r['session']}" if "session" in r else
                 f"membership:{instrument}:{r['valid_from']}") for r in used
            }))
            results.append(Signal(instrument, decision_at, window[-2], latest, score,
                                  score is not None, reason, input_keys))
        history = [r for r in known_memberships if r["instrument_id"] == instrument
                   and r["valid_from"] <= formation and (r["valid_to"] is None or r["valid_to"] >= window[0])]
        used.extend(history)
        required_days = [r["session"] for r in past if r["session"] >= window[0]]
        if any(not any(r["status"] in ("listed", "suspended") and r["valid_from"] <= day
                       and (r["valid_to"] is None or day <= r["valid_to"]) for r in history)
               for day in required_days):
            finish(None, "insufficient_membership_history")
            continue
        monthly = [bars.get((instrument, day)) for day in window]
        used.extend(row for row in monthly if row is not None)
        if any(row is None for row in monthly):
            finish(None, "missing_monthly_close")
            continue
        if Decimal(str(monthly[-1]["close"])) < 2:
            finish(None, "low_price")
            continue
        daily = [bars.get((instrument, day)) for day in recent_sessions]
        used.extend(row for row in daily if row is not None)
        valid = [row for row in daily if row is not None and row["volume_shares"] > 0
                 and Decimal(str(row["volume_brl"])) > 0]
        if len(recent_sessions) < 63 or len(valid) < 50 or median(Decimal(str(row["volume_brl"])) for row in valid) < 1_000_000:
            finish(None, "insufficient_liquidity")
            continue
        # Reinvest known cash distributions at the ex-session close. Splits
        # change shares, never create an artificial loss in the score.
        shares = Decimal(1)
        start = Decimal(str(monthly[0]["close"]))
        relevant = sorted((r for r in actions if r["instrument_id"] == instrument
                           and window[0] < r["ex_session"] <= window[-2]),
                          key=lambda r: (r["ex_session"], r["action_id"]))
        for ex_session, rows in groupby(relevant, key=lambda r: r["ex_session"]):
            events = list(rows)
            used.extend(events)
            if any(action["kind"] == "delisting" for action in events):
                shares = None
                break
            for action in events:
                if action["kind"] == "split":
                    shares *= Decimal(str(action["ratio"]))
            # Cash per share is defined on the post-split unit. Same-day cash
            # distributions are summed before a single close reinvestment.
            cash_per_share = sum((Decimal(str(r["cash_per_share"])) for r in events
                                  if r["kind"] == "dividend"), Decimal(0))
            if cash_per_share:
                ex_bar = bars.get((instrument, ex_session))
                if ex_bar is None:
                    shares = None
                    break
                used.append(ex_bar)
                shares *= 1 + cash_per_share / Decimal(str(ex_bar["close"]))
        if shares is None:
            finish(None, "incomplete_corporate_action")
        else:
            finish(shares * Decimal(str(monthly[-2]["close"])) / start - 1, "ok")
    return tuple(sorted(results, key=lambda s: s.instrument_id))
