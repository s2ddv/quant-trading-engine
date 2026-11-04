"""One synthetic monthly rebalance after the original F1 formation."""

from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, ROUND_DOWN, localcontext
from hashlib import sha256
import json

from qtre.calendar import formation_sessions
from qtre.signals import momentum_12_2
from qtre.universe import listed_members

from . import F1Config, _Book, _affordable_fill, _quote, instant, money, run_f1


REBALANCE_MODEL = "synthetic-f1-two-formations-v2"


def _mark(snapshot, book, day, valued_at):
    closes = {row["instrument_id"]: row for row in snapshot.available("bars", valued_at)
              if row["session"] == day}
    missing = sorted(ident for ident, quantity in book.positions.items()
                     if quantity and (ident not in closes or ident in book.unresolved))
    marks = {ident: dict(quantity=quantity, price=Decimal(str(closes[ident]["close"])),
                         source_key=f"bar:{ident}:{day}")
             for ident, quantity in book.positions.items()
             if quantity and ident in closes and ident not in book.unresolved}
    value = money(sum((r["quantity"] * r["price"] for r in marks.values()), Decimal(0)))
    due = sum(book.receivables.values(), Decimal(0))
    return dict(session=day, valued_at=valued_at,
                status="NAV_INCOMPLETO" if missing else "COMPLETE", cash_brl=book.cash,
                receivable_brl=due, positions_value_brl=None if missing else value,
                nav_brl=None if missing else money(book.cash + due + value),
                missing_marks=missing, marks=marks)


def _sell_quote(opening, quantity, config, position_quantity, cost_basis):
    spread = config.half_spread_bps / 10000
    slippage = config.slippage_bps / 10000
    price = opening * (1 - spread - slippage)
    if price <= 0:
        raise ValueError("sell execution price must be positive")
    reference = money(opening * quantity)
    notional = money(price * quantity)
    spread_cost = min(reference - notional, money(opening * quantity * spread))
    slippage_cost = reference - notional - spread_cost
    fees = money(notional * config.fees_bps / 10000)
    credit = notional - fees
    if credit < 0:
        raise ValueError("sell fees exceed proceeds")
    removed = cost_basis if quantity == position_quantity else money(cost_basis * quantity / position_quantity)
    return dict(price=price, reference_price=opening, reference_notional=reference,
                notional_brl=notional, spread_cost=spread_cost, slippage_cost=slippage_cost,
                fees=fees, cash_credit=credit, basis_removed=removed,
                realized_pnl=credit - removed)


def run_f1_two_formations(snapshot, *, first_decision_at: datetime,
                          second_decision_at: datetime, config: F1Config = F1Config()):
    """Run the existing first formation, then sell and rebalance at the next month end."""
    with localcontext(Context(prec=28)):
        return _run_two(snapshot, first_decision_at, second_decision_at, config)


def _run_two(snapshot, first_decision_at, second_decision_at, config):
    first = run_f1(snapshot, decision_at=first_decision_at, config=config)
    snapshot.check_as_of(second_decision_at)
    config.validate()
    if second_decision_at <= first_decision_at:
        raise ValueError("second decision must follow the first")
    second_decision_at = second_decision_at.astimezone(timezone.utc)
    formation = formation_sessions(snapshot, second_decision_at)[-1]
    day = formation["session"]
    first_year, first_month = map(int, first["manifest"]["formation_session"][:7].split("-"))
    next_month = f"{first_year + (first_month == 12):04d}-{first_month % 12 + 1:02d}"
    if day[:7] != next_month:
        raise ValueError("second formation must be in the next calendar month")
    if day <= first["nav"][-1]["session"]:
        raise ValueError("second formation overlaps the first execution window")
    if first["nav"][-1]["status"] != "COMPLETE":
        raise ValueError("second formation requires a complete opening NAV")

    sessions = [s for s in snapshot.payload["calendar"]["sessions"]
                if instant(s["open_at"]) > second_decision_at][:config.expiry_sessions]
    if len(sessions) != config.expiry_sessions:
        raise ValueError("snapshot lacks the second order expiry window")
    for session in sessions:
        snapshot.check_as_of(instant(session["close_at"]) + timedelta(minutes=config.mark_delay_minutes))

    last_by_ident = {row["instrument_id"]: row for row in first["ledger"]}
    book = _Book(first["nav"][-1]["cash_brl"])
    book.positions = {ident: row["quantity"] for ident, row in last_by_ident.items() if row["quantity"]}
    book.cost_basis = {ident: row["cost_basis"] for ident, row in last_by_ident.items() if row["quantity"]}
    actions_by_id = {action["action_id"]: action for action in snapshot.available("actions", second_decision_at)}
    unpaid = {row["event_id"]: row for row in first["ledger"] if row["kind"] == "dividend_ex"}
    for row in first["ledger"]:
        if row["kind"] == "dividend_pay":
            unpaid.pop(row["event_id"].removesuffix("-pay"), None)
    book.receivables = {action_id: money(Decimal(row["quantity"]) *
                                         Decimal(str(actions_by_id[action_id]["cash_per_share"])))
                        for action_id, row in unpaid.items()}
    if sum(book.receivables.values(), Decimal(0)) != first["nav"][-1]["receivable_brl"]:
        raise ValueError("opening receivables do not reconcile")
    bridge = [s for s in snapshot.payload["calendar"]["sessions"]
              if first["nav"][-1]["session"] < s["session"] <= day]
    bridge_nav = []
    for session in bridge:
        bridge_day = session["session"]
        open_at = instant(session["open_at"])
        valued_at = instant(session["close_at"]) + timedelta(minutes=config.mark_delay_minutes)
        snapshot.check_as_of(valued_at)
        if bridge_day == day and valued_at > second_decision_at:
            raise ValueError("second decision precedes formation mark")
        book.actions(snapshot, bridge_day, open_at, bridge[0]["session"], {})
        book.actions(snapshot, bridge_day, valued_at, bridge[0]["session"], {})
        bridge_nav.append(_mark(snapshot, book, bridge_day, valued_at))
    formation_nav = bridge_nav[-1]
    if formation_nav["status"] != "COMPLETE":
        raise ValueError("second formation has incomplete NAV")
    signals = momentum_12_2(snapshot, decision_at=second_decision_at, formation_session=day)
    selected = sorted((s for s in signals if s.eligible), key=lambda s: (-s.score, s.instrument_id))[:10]
    if len(selected) < 5:
        raise ValueError("second formation requires five eligible instruments")
    weight = min(Decimal(1) / len(selected), config.max_name_weight)
    eligible = {s.instrument_id: s for s in selected}
    bars = snapshot.available("bars", second_decision_at)
    formation_bars = {bar["instrument_id"]: bar for bar in bars if bar["session"] == day}
    histories = {}
    for bar in bars:
        histories.setdefault(bar["instrument_id"], []).append(bar)
    orders = []
    for ident in sorted(set(book.positions) | set(eligible)):
        if ident not in formation_bars:
            raise ValueError(f"missing formation close for {ident}")
        ref = Decimal(str(formation_bars[ident]["close"]))
        desired = int((formation_nav["nav_brl"] * (weight if ident in eligible else 0) / ref)
                      .to_integral_value(rounding=ROUND_DOWN))
        delta = desired - book.positions.get(ident, 0)
        quantity = abs(delta) // config.lot * config.lot
        if not quantity:
            continue
        history = sorted(histories[ident], key=lambda r: r["session"])
        capacity = int(Decimal(min(r["volume_shares"] for r in history[-50:])) * config.max_participation) if len(history) >= 50 else 0
        input_keys = set(eligible[ident].input_keys if ident in eligible else ())
        input_keys.update(f"bar:{ident}:{r['session']}" for r in history[-50:])
        orders.append(dict(order_id=f"O2-{ident}", formation_id="second", instrument_id=ident,
                           created_at=second_decision_at, earliest_execution_at=instant(sessions[0]["open_at"]),
                           side="buy" if delta > 0 else "sell", quantity=quantity,
                           target_weight=weight if ident in eligible else Decimal(0),
                           expiry_session=sessions[-1]["session"], reference_session=day,
                           reference_price=ref, capacity_shares=capacity,
                           input_keys=tuple(sorted(input_keys))))
    states = {o["order_id"]: dict(order_id=o["order_id"], instrument_id=o["instrument_id"],
                                  remaining=o["quantity"], filled=0, status="PENDING",
                                  reason="awaiting_open") for o in orders}
    fills, nav = [], [formation_nav]
    first_day = sessions[0]["session"]
    for session in sessions:
        trade_day, open_at = session["session"], instant(session["open_at"])
        valued_at = instant(session["close_at"]) + timedelta(minutes=config.mark_delay_minutes)
        book.actions(snapshot, trade_day, open_at, first_day, states)
        members = set(listed_members(snapshot, trade_day, as_of=open_at))
        opens = {r["instrument_id"]: r for r in snapshot.available("opens", open_at) if r["session"] == trade_day}
        for order in sorted(orders, key=lambda o: (o["side"] != "sell", o["order_id"])):
            state = states[order["order_id"]]
            if state["status"] != "PENDING":
                continue
            ident = order["instrument_id"]
            event = opens.get(ident)
            if ident not in members or event is None or not event["tradable"]:
                state["reason"] = "unavailable_or_untradable"
                continue
            opening = Decimal(str(event["open_price"]))
            maximum = min(state["remaining"], order["capacity_shares"])
            if order["side"] == "sell":
                quantity = min(maximum, book.positions.get(ident, 0)) // config.lot * config.lot
            else:
                quantity = _affordable_fill(opening, maximum, book.cash, config)
            if not quantity:
                state["reason"] = "cash_or_capacity"
                continue
            if order["side"] == "sell":
                quote = _sell_quote(opening, quantity, config, book.positions[ident], book.cost_basis[ident])
                book.cash += quote["cash_credit"]
                book.positions[ident] -= quantity
                book.cost_basis[ident] -= quote["basis_removed"]
            else:
                quote = _quote(opening, quantity, config)
                book.cash -= quote["cash_debit"]
                book.positions[ident] = book.positions.get(ident, 0) + quantity
                book.cost_basis[ident] = book.cost_basis.get(ident, Decimal(0)) + quote["cash_debit"]
            state["remaining"] -= quantity
            state["filled"] += quantity
            if not state["remaining"]:
                state.update(status="FILLED", reason="complete")
            fill_id = f"F-{order['order_id']}-{trade_day}"
            fills.append(dict(fill_id=fill_id, order_id=order["order_id"], instrument_id=ident,
                              executed_at=open_at, session=trade_day, side=order["side"], quantity=quantity,
                              **quote, source_key=f"open:{ident}:{trade_day}",
                              input_available_at=instant(event["available_at"]), model_id=REBALANCE_MODEL))
            book.record(fill_id, trade_day, order["side"], ident,
                        quote["cash_credit"] if order["side"] == "sell" else -quote["cash_debit"])
        book.actions(snapshot, trade_day, valued_at, first_day, states)
        nav.append(_mark(snapshot, book, trade_day, valued_at))
    for state in states.values():
        if state["status"] == "PENDING":
            state.update(status="EXPIRED", reason="expiry_session_reached")

    manifest = dict(first["manifest"])
    manifest.update(schema_version=4, model_id=REBALANCE_MODEL,
                    second_decision_at=second_decision_at.isoformat(), second_formation_session=day,
                    bridge_sessions=[s["session"] for s in bridge],
                    decision_windows=[dict(decision_at=first["manifest"]["decision_at"],
                                           formation_session=first["manifest"]["formation_session"],
                                           execution_sessions=[r["session"] for r in first["nav"]]),
                                      dict(decision_at=second_decision_at.isoformat(),
                                           formation_session=day,
                                           execution_sessions=[r["session"] for r in sessions])])
    del manifest["run_id"]
    manifest["run_id"] = sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return dict(manifest=manifest, signals=first["signals"] + signals,
                orders=first["orders"] + tuple(orders),
                order_states=first["order_states"] + tuple(states.values()),
                fills=first["fills"] + tuple(fills), ledger=first["ledger"] + tuple(book.ledger),
                nav=first["nav"] + tuple(bridge_nav[:-1]) + tuple(nav), formation_nav=formation_nav)
