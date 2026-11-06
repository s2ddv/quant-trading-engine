"""One synthetic formation followed by a bounded, causal execution window."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
from pathlib import Path
import platform

from qtre.calendar import formation_sessions
from qtre.data.snapshot import Snapshot
from qtre.signals import momentum_12_2
from qtre.universe import listed_members


CENT = Decimal("0.01")
MODEL_VERSION = "synthetic-f1-v2"


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def instant(value: str) -> datetime:
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
    opening_reserve: Decimal = Decimal("0.01")
    expiry_sessions: int = 3
    mark_delay_minutes: int = 6

    def validate(self) -> None:
        for name in ("initial_cash", "max_name_weight", "half_spread_bps", "slippage_bps",
                     "fees_bps", "max_participation", "opening_reserve"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError(f"{name}: expected finite non-negative Decimal")
        if self.initial_cash <= 0 or money(self.initial_cash) != self.initial_cash:
            raise ValueError("initial_cash must be positive and expressed in whole cents")
        if not 0 < self.max_name_weight <= 1 or not 0 < self.max_participation <= 1:
            raise ValueError("weight and participation must be in (0, 1]")
        for name in ("lot", "expiry_sessions", "mark_delay_minutes"):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name == "mark_delay_minutes" else 1):
                raise ValueError(f"{name}: invalid integer")


def _quote(opening: Decimal, quantity: int, config: F1Config) -> dict:
    # Keep per-share precision. Only monetary postings are rounded to cents.
    spread = config.half_spread_bps / 10000
    slippage = config.slippage_bps / 10000
    price = opening * (1 + spread + slippage)
    base = money(opening * quantity)
    notional = money(price * quantity)
    spread_cost = min(notional - base, money(opening * quantity * spread))
    # Allocate the cent residual to slippage so the posted rubrics reconcile.
    slippage_cost = notional - base - spread_cost
    fees = money(notional * config.fees_bps / 10000)
    return dict(price=price, reference_price=opening, reference_notional=base,
                notional_brl=notional, spread_cost=spread_cost,
                slippage_cost=slippage_cost, fees=fees, cash_debit=notional + fees)


def _affordable_fill(opening, maximum, cash, config):
    """Largest whole lot whose rounded debit fits cash (including fees)."""
    low, high = 0, maximum // config.lot
    while low < high:
        middle = (low + high + 1) // 2
        if _quote(opening, middle * config.lot, config)["cash_debit"] <= cash:
            low = middle
        else:
            high = middle - 1
    return low * config.lot


def _plan_orders(snapshot, signals, decision_at, sessions, config, *, equal_weight=False):
    selected = sorted((s for s in signals if s.eligible),
                      key=(lambda s: s.instrument_id) if equal_weight else
                      (lambda s: (-s.score, s.instrument_id)))
    if not equal_weight:
        selected = selected[:10]
    if not selected or (not equal_weight and len(selected) < 5):
        return (), "no_eligible" if equal_weight else "fewer_than_five_eligible"
    weight = min(Decimal(1) / len(selected), config.max_name_weight)
    reserve = (1 + (config.half_spread_bps + config.slippage_bps + config.fees_bps) / 10000
               + config.opening_reserve)
    bars = snapshot.available("bars", decision_at)
    histories = {}
    for bar in bars:
        histories.setdefault(bar["instrument_id"], []).append(bar)
    orders = []
    for signal in selected:
        history = sorted(histories[signal.instrument_id], key=lambda r: r["session"])
        ref_bar = history[-1]
        ref = Decimal(str(ref_bar["close"]))
        quantity = int((config.initial_cash * weight / (ref * reserve)).to_integral_value(rounding=ROUND_DOWN))
        quantity = quantity // config.lot * config.lot
        capacity = int(Decimal(min(r["volume_shares"] for r in history[-50:])) * config.max_participation) if len(history) >= 50 else 0
        if quantity:
            orders.append(dict(order_id=f"O-{signal.instrument_id}", instrument_id=signal.instrument_id,
                               created_at=decision_at, earliest_execution_at=instant(sessions[0]["open_at"]),
                               side="buy", quantity=quantity, target_weight=weight,
                               expiry_session=sessions[-1]["session"], reference_session=ref_bar["session"],
                               reference_price=ref, capacity_shares=capacity,
                               input_keys=tuple(f"bar:{signal.instrument_id}:{r['session']}" for r in history[-50:])))
    return tuple(orders), "targets_formed"


class _Book:
    def __init__(self, cash):
        self.cash = cash
        self.positions = {}
        self.cost_basis = {}  # total acquisition cost including fees, not per-share
        self.receivables = {}
        self.ledger = []
        self.processed = set()
        self.unresolved = set()

    def record(self, event_id, day, kind, ident, cash_delta=Decimal(0)):
        self.ledger.append(dict(event_id=event_id, session=day, kind=kind, instrument_id=ident,
                                quantity=self.positions.get(ident, 0), cost_basis=self.cost_basis.get(ident, Decimal(0)),
                                cash_delta=cash_delta, cash_brl=self.cash,
                                receivable_brl=sum(self.receivables.values(), Decimal(0))))

    def actions(self, snapshot, day, as_of, first_day, states):
        known = sorted(snapshot.available("actions", as_of),
                       key=lambda a: (a["ex_session"], {"split": 0, "dividend": 1, "delisting": 2}[a["kind"]], a["action_id"]))
        clocks = {s["session"]: instant(s["open_at"]) for s in snapshot.payload["calendar"]["sessions"]}
        for action in known:
            ex_day, ident, action_id = action["ex_session"], action["instrument_id"], action["action_id"]
            if ex_day < first_day or ex_day > day or action_id in self.processed:
                continue
            pending = [s for s in states.values() if s["instrument_id"] == ident and s["remaining"] and s["status"] == "PENDING"]
            quantity = self.positions.get(ident, 0)
            if (quantity or pending) and instant(action["available_at"]) > clocks[ex_day]:
                raise ValueError(f"late corporate action {action_id}: cannot reconstruct ex-session entitlement")
            self.processed.add(action_id)
            if action["kind"] in ("split", "delisting"):
                for state in pending:
                    state.update(status="CANCELLED", reason=f"{action['kind']}_requires_new_order")
            if action["kind"] == "split" and quantity:
                updated = Decimal(quantity) * Decimal(str(action["ratio"]))
                if updated != int(updated):
                    raise ValueError("fractional split requires a declared cash-in-lieu rule")
                self.positions[ident] = int(updated)
                self.record(action_id, day, "split", ident)
            elif action["kind"] == "dividend" and quantity:
                self.receivables[action_id] = money(Decimal(quantity) * Decimal(str(action["cash_per_share"])))
                self.record(action_id, day, "dividend_ex", ident)
            elif action["kind"] == "delisting" and quantity:
                if "exit_cash_per_share" in action:
                    credit = money(Decimal(quantity) * Decimal(str(action["exit_cash_per_share"])))
                    removed = self.cost_basis.pop(ident, Decimal(0))
                    self.positions[ident] = 0
                    self.receivables[action_id] = credit
                    self.record(action_id, day, "delisting_ex", ident)
                    self.ledger[-1].update(basis_removed=removed, realized_pnl=credit - removed)
                else:
                    self.unresolved.add(ident)
                    self.record(action_id, day, "unresolved_delisting", ident)
        for action in known:
            if action.get("pay_session") == day and action["action_id"] in self.receivables:
                payment = self.receivables.pop(action["action_id"])
                self.cash += payment
                kind = "delisting_pay" if action["kind"] == "delisting" else "dividend_pay"
                self.record(action["action_id"] + "-pay", day, kind, action["instrument_id"], payment)


def _code_hash() -> str:
    root = Path(__file__).resolve().parents[1]
    content = [(p.relative_to(root).as_posix(), sha256(p.read_bytes()).hexdigest())
               for p in sorted(root.rglob("*.py"))]
    return sha256(json.dumps(content, separators=(",", ":")).encode()).hexdigest()


def run_f1(snapshot: Snapshot, *, decision_at: datetime, config: F1Config = F1Config(),
           formation_session: str | None = None, control_id: str | None = None):
    """A single formation. Sales and repeated rebalancing are outside this API."""
    with localcontext(Context(prec=28)):
        snapshot.check_as_of(decision_at)
        config.validate()
        if control_id not in (None, "cash", "equal_weight"):
            raise ValueError("unknown synthetic control")
        return _run(snapshot, decision_at.astimezone(timezone.utc), config, formation_session, control_id)


def _run(snapshot, decision_at, config, formation_session, control_id):
    formation = formation_sessions(snapshot, decision_at, formation_session)[-1]["session"]
    signals = (() if control_id == "cash" else
               momentum_12_2(snapshot, decision_at=decision_at, formation_session=formation))
    sessions = [r for r in snapshot.payload["calendar"]["sessions"] if instant(r["open_at"]) > decision_at][:config.expiry_sessions]
    if len(sessions) != config.expiry_sessions:
        raise ValueError("snapshot lacks the full order expiry window")
    for session in sessions:
        snapshot.check_as_of(instant(session["close_at"]) + timedelta(minutes=config.mark_delay_minutes))
    orders, portfolio_reason = (((), "cash_control") if control_id == "cash" else
                                _plan_orders(snapshot, signals, decision_at, sessions, config,
                                             equal_weight=control_id == "equal_weight"))
    states = {o["order_id"]: dict(order_id=o["order_id"], instrument_id=o["instrument_id"],
                                  remaining=o["quantity"], filled=0, status="PENDING", reason="awaiting_open") for o in orders}
    book = _Book(config.initial_cash)
    fills, nav = [], []
    first_day = sessions[0]["session"]
    for session in sessions:
        day, open_at = session["session"], instant(session["open_at"])
        close_cut = instant(session["close_at"]) + timedelta(minutes=config.mark_delay_minutes)
        book.actions(snapshot, day, open_at, first_day, states)
        members = set(listed_members(snapshot, day, as_of=open_at))
        opens = {r["instrument_id"]: r for r in snapshot.available("opens", open_at, session=day)}
        for order in orders:
            state = states[order["order_id"]]
            if state["status"] != "PENDING":
                continue
            ident = order["instrument_id"]
            event = opens.get(ident)
            if ident not in members or event is None or not event["tradable"]:
                state["reason"] = "unavailable_or_untradable"
                continue
            opening = Decimal(str(event["open_price"]))
            quantity = _affordable_fill(opening, min(state["remaining"], order["capacity_shares"]), book.cash, config)
            if not quantity:
                state["reason"] = "cash_or_capacity"
                continue
            quote = _quote(opening, quantity, config)
            book.cash -= quote["cash_debit"]
            state["remaining"] -= quantity
            state["filled"] += quantity
            if not state["remaining"]:
                state.update(status="FILLED", reason="complete")
            book.positions[ident] = book.positions.get(ident, 0) + quantity
            book.cost_basis[ident] = book.cost_basis.get(ident, Decimal(0)) + quote["cash_debit"]
            fill_id = f"F-{order['order_id']}-{day}"
            fills.append(dict(fill_id=fill_id, order_id=order["order_id"], instrument_id=ident,
                              executed_at=open_at, session=day, quantity=quantity, **quote,
                              source_key=f"open:{ident}:{day}", input_available_at=instant(event["available_at"]),
                              model_id=MODEL_VERSION))
            book.record(fill_id, day, "buy", ident, -quote["cash_debit"])
        # Detect late corporate actions when they become known, never by looking
        # ahead at the entire snapshot while constructing earlier orders.
        book.actions(snapshot, day, close_cut, first_day, states)
        closes = {r["instrument_id"]: r for r in snapshot.available("bars", close_cut, session=day)}
        missing = sorted(ident for ident, quantity in book.positions.items()
                         if quantity and (ident not in closes or ident in book.unresolved))
        marks = {ident: dict(quantity=quantity, price=Decimal(str(closes[ident]["close"])),
                             source_key=f"bar:{ident}:{day}") for ident, quantity in book.positions.items()
                 if quantity and ident in closes and ident not in book.unresolved}
        value = money(sum((r["quantity"] * r["price"] for r in marks.values()), Decimal(0)))
        receivable = sum(book.receivables.values(), Decimal(0))
        nav.append(dict(session=day, valued_at=close_cut, status="NAV_INCOMPLETO" if missing else "COMPLETE",
                        cash_brl=book.cash, receivable_brl=receivable,
                        positions_value_brl=None if missing else value,
                        nav_brl=None if missing else money(book.cash + receivable + value),
                        missing_marks=missing, marks=marks))
    for state in states.values():
        if state["status"] == "PENDING":
            state.update(status="EXPIRED", reason="expiry_session_reached")
    config_data = {key: str(value) for key, value in vars(config).items()}
    manifest = dict(schema_version=2, synthetic=True, snapshot_hash=snapshot.content_hash,
                    calendar_id=snapshot.calendar_id, code_hash=_code_hash(), model_id=MODEL_VERSION,
                    python_version=platform.python_version(), decimal_precision=28,
                    monetary_rounding="ROUND_HALF_UP; slippage absorbs cent residual",
                    settlement="synthetic_immediate", formation_session=formation,
                    decision_at=decision_at.isoformat(), config=config_data)
    if control_id is not None:
        manifest["control_id"] = control_id
        manifest["model_id"] = f"synthetic-f2-{control_id}-v1"
    if any(row["kind"] == "delisting_ex" for row in book.ledger):
        manifest["event_schema_version"] = 2
    manifest["run_id"] = sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return dict(manifest=manifest, signals=signals, orders=orders, order_states=tuple(states.values()),
                portfolio_reason=portfolio_reason, fills=tuple(fills), ledger=tuple(book.ledger), nav=tuple(nav))


from .rebalance import run_f1_monthly, run_f1_two_formations, run_f2_control
