"""Point-in-time research signals."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from statistics import median

from qtre.data.snapshot import Snapshot
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


def momentum_12_2(snapshot: Snapshot, *, decision_at: datetime) -> tuple[Signal, ...]:
    """Score the next execution month using 13 consecutive monthly closes."""
    sessions = snapshot.payload["calendar"]["sessions"]
    past = [row for row in sessions if datetime.fromisoformat(row["close_at"].replace("Z", "+00:00")) < decision_at]
    if not past:
        raise ValueError("decision precedes every complete session")
    formation = past[-1]["session"]
    months: dict[str, str] = {}
    for row in past:
        months[row["session"][:7]] = row["session"]
    keys = sorted(months)
    if formation != months[keys[-1]] or len(keys) < 13:
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
    recent_sessions = [r["session"] for r in past[-63:]]
    results = []
    for instrument in memberships:
        used = []
        def finish(score, reason):
            latest = max((datetime.fromisoformat(r["available_at"].replace("Z", "+00:00")) for r in used), default=None)
            results.append(Signal(instrument, decision_at, window[-2], latest, score, score is not None, reason))
        membership = next(r for r in snapshot.available("memberships", decision_at)
                          if r["instrument_id"] == instrument and r["valid_from"] <= formation
                          and (r["valid_to"] is None or formation <= r["valid_to"]))
        used.append(membership)
        if membership["valid_from"] > window[0]:
            finish(None, "insufficient_membership_history")
            continue
        monthly = [bars.get((instrument, day)) for day in window]
        if any(row is None for row in monthly):
            finish(None, "missing_monthly_close")
            continue
        used.extend(monthly)
        if Decimal(str(monthly[-1]["close"])) < 2:
            finish(None, "low_price")
            continue
        daily = [bars.get((instrument, day)) for day in recent_sessions]
        valid = [row for row in daily if row is not None]
        used.extend(valid)
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
        for action in relevant:
            used.append(action)
            if action["kind"] == "split":
                shares *= Decimal(str(action["ratio"]))
            elif action["kind"] == "dividend":
                ex_bar = bars.get((instrument, action["ex_session"]))
                if ex_bar is None:
                    shares = None
                    break
                used.append(ex_bar)
                shares += shares * Decimal(str(action["cash_per_share"])) / Decimal(str(ex_bar["close"]))
            else:
                shares = None
                break
        if shares is None:
            finish(None, "incomplete_corporate_action")
        else:
            finish(shares * Decimal(str(monthly[-2]["close"])) / start - 1, "ok")
    return tuple(sorted(results, key=lambda s: s.instrument_id))
