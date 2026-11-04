"""Small deterministic synthetic F1 event loop."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from hashlib import sha256
import json

from qtre.data.snapshot import Snapshot
from qtre.signals import momentum_12_2


CENT = Decimal("0.01")


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class F1Config:
    initial_cash: Decimal = Decimal("100000")
    max_name_weight: Decimal = Decimal("0.10")
    lot: int = 1
    half_spread_bps: Decimal = Decimal("5")
    slippage_bps: Decimal = Decimal("5")
    fees_bps: Decimal = Decimal("5")
    max_participation: Decimal = Decimal("0.05")


def run_f1(snapshot: Snapshot, *, decision_at: datetime, config: F1Config = F1Config()):
    """Form once, fill at later opens, and mark three synthetic sessions."""
    if decision_at.tzinfo is None or decision_at > snapshot.as_of:
        raise ValueError("decision_at must be timezone-aware and inside snapshot")
    if (config.initial_cash <= 0 or config.lot <= 0 or not Decimal(0) < config.max_name_weight <= 1
            or not Decimal(0) < config.max_participation <= 1
            or min(config.half_spread_bps, config.slippage_bps, config.fees_bps) < 0):
        raise ValueError("invalid F1 cash, lot, weight, capacity or costs")
    signals = momentum_12_2(snapshot, decision_at=decision_at)
    selected = sorted((s for s in signals if s.eligible), key=lambda s: (-s.score, s.instrument_id))[:10]
    if len(selected) < 5:
        selected = []
    sessions = snapshot.payload["calendar"]["sessions"]
    # The final completed session of the preceding month is the sizing reference.
    previous = [r for r in sessions if instant(r["close_at"]) < decision_at][-1]
    formation_day = previous["session"]
    bars_at_decision = {(r["instrument_id"], r["session"]): r for r in snapshot.available("bars", decision_at)}
    next_sessions = [r for r in sessions if instant(r["open_at"]) > decision_at][:3]
    if not next_sessions:
        raise ValueError("no subsequent session in snapshot")
    orders = []
    weight = min(Decimal(1) / len(selected), config.max_name_weight) if selected else Decimal(0)
    reserve = Decimal(1) + (config.half_spread_bps + config.slippage_bps + config.fees_bps) / 10000 + Decimal("0.01")
    for signal in selected:
        ref = Decimal(str(bars_at_decision[(signal.instrument_id, formation_day)]["close"]))
        quantity = int((config.initial_cash * weight / (ref * reserve)).to_integral_value(rounding=ROUND_DOWN))
        quantity = quantity // config.lot * config.lot
        if quantity:
            orders.append(dict(order_id=f"O-{signal.instrument_id}", instrument_id=signal.instrument_id,
                               created_at=decision_at, earliest_execution_at=instant(next_sessions[0]["open_at"]),
                               side="buy", quantity=quantity, remaining=quantity, target_weight=weight,
                               expiry_session=next_sessions[-1]["session"]))
    cash = money(config.initial_cash)
    positions = {}
    receivables = {}
    fills = []
    ledger = []
    nav = []
    for session in next_sessions:
        day = session["session"]
        open_at = instant(session["open_at"])
        close_cut = instant(session["close_at"]).replace(minute=6)
        # Actions are published before this opening and applied at ex-session.
        for action in snapshot.available("actions", open_at):
            if action["ex_session"] != day:
                continue
            ident = action["instrument_id"]
            quantity = positions.get(ident, 0)
            if action["kind"] == "split" and quantity:
                new_quantity = Decimal(quantity) * Decimal(str(action["ratio"]))
                if new_quantity != int(new_quantity):
                    raise ValueError("fractional split requires a declared cash-in-lieu rule")
                positions[ident] = int(new_quantity)
                ledger.append(dict(event_id=action["action_id"], session=day, kind="split", instrument_id=ident,
                                   quantity=positions[ident], cash_brl=cash, receivable_brl=sum(receivables.values(), Decimal(0))))
            elif action["kind"] == "dividend" and quantity:
                amount = money(Decimal(quantity) * Decimal(str(action["cash_per_share"])))
                receivables[action["action_id"]] = amount
                ledger.append(dict(event_id=action["action_id"], session=day, kind="dividend_ex", instrument_id=ident,
                                   quantity=quantity, cash_brl=cash, receivable_brl=sum(receivables.values(), Decimal(0))))
        for action in snapshot.available("actions", open_at):
            if action.get("pay_session") == day and action["action_id"] in receivables:
                cash += receivables.pop(action["action_id"])
                ledger.append(dict(event_id=action["action_id"] + "-pay", session=day, kind="dividend_pay",
                                   instrument_id=action["instrument_id"], cash_brl=cash,
                                   receivable_brl=sum(receivables.values(), Decimal(0))))
        opens = {(r["instrument_id"], r["session"]): r for r in snapshot.available("opens", open_at)}
        for order in orders:
            if order["remaining"] <= 0 or open_at < order["earliest_execution_at"]:
                continue
            event = opens.get((order["instrument_id"], day))
            if event is None or not event["tradable"]:
                continue
            opening = Decimal(str(event["open_price"]))
            spread = config.half_spread_bps / 10000
            slip = config.slippage_bps / 10000
            fee_rate = config.fees_bps / 10000
            price = money(opening * (1 + spread + slip))
            # Capacity uses only historical volume already published at decision.
            history = [Decimal(str(r["volume_shares"])) for (ident, session_day), r in bars_at_decision.items()
                       if ident == order["instrument_id"] and session_day <= formation_day]
            capacity = int(min(history[-50:]) * config.max_participation) if len(history) >= 50 else 0
            affordable = int((cash / (price * (1 + fee_rate))).to_integral_value(rounding=ROUND_DOWN))
            quantity = min(order["remaining"], capacity, affordable)
            quantity = quantity // config.lot * config.lot
            if not quantity:
                continue
            fee = money(price * quantity * fee_rate)
            total = money(price * quantity + fee)
            while quantity and total > cash:
                quantity -= config.lot
                fee = money(price * quantity * fee_rate)
                total = money(price * quantity + fee)
            if not quantity:
                continue
            cash -= total
            order["remaining"] -= quantity
            positions[order["instrument_id"]] = positions.get(order["instrument_id"], 0) + quantity
            fills.append(dict(fill_id=f"F-{order['order_id']}-{day}", order_id=order["order_id"],
                              executed_at=open_at, session=day, quantity=quantity, price=price,
                              spread_cost=money(opening * quantity * spread),
                              slippage_cost=money(opening * quantity * slip), fees=fee,
                              model_id="next_open-v1"))
            ledger.append(dict(event_id=fills[-1]["fill_id"], session=day, kind="buy",
                               instrument_id=order["instrument_id"], quantity=positions[order["instrument_id"]],
                               cash_brl=cash, receivable_brl=sum(receivables.values(), Decimal(0))))
        closes = {(r["instrument_id"], r["session"]): r for r in snapshot.available("bars", close_cut)}
        missing = sorted(ident for ident, quantity in positions.items() if quantity and (ident, day) not in closes)
        value = sum((Decimal(quantity) * Decimal(str(closes[(ident, day)]["close"]))
                     for ident, quantity in positions.items() if (ident, day) in closes), Decimal(0))
        status = "NAV_INCOMPLETO" if missing else "COMPLETE"
        nav.append(dict(session=day, status=status, cash_brl=cash,
                        receivable_brl=sum(receivables.values(), Decimal(0)),
                        positions_value_brl=money(value) if not missing else None,
                        nav_brl=money(cash + sum(receivables.values(), Decimal(0)) + value) if not missing else None,
                        missing_marks=missing))
    config_data = {key: str(value) for key, value in vars(config).items()}
    manifest = dict(schema_version=1, synthetic=True, snapshot_hash=snapshot.content_hash,
                    decision_at=decision_at.isoformat(), config=config_data,
                    run_id=sha256(json.dumps([snapshot.content_hash, decision_at.isoformat(), config_data],
                                            sort_keys=True).encode()).hexdigest())
    return dict(manifest=manifest, signals=signals, orders=tuple(orders), fills=tuple(fills),
                ledger=tuple(ledger), nav=tuple(nav))
