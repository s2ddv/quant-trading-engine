"""Versioned F1 artifacts and independent synthetic book replay."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
from pathlib import Path

from qtre.data.snapshot import Snapshot, parse_snapshot
from qtre.universe import listed_members


FILES = ("snapshot.json", "orders.jsonl", "order_states.jsonl", "fills.jsonl", "ledger.jsonl", "nav.jsonl")
TABLES = ("orders", "order_states", "fills", "ledger", "nav")
SCHEMA_VERSION = 1
REBALANCE_SCHEMA_VERSION = 2
CONTINUOUS_SCHEMA_VERSION = 3
MONTHLY_SCHEMA_VERSION = 4
DELISTING_SCHEMA_VERSION = 5
CENT = Decimal("0.01")


class ReplayError(ValueError):
    """Persisted run is incomplete, altered, or fails book reconciliation."""


def _plain(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal in artifact")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp without timezone in artifact")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _json(value):
    return json.dumps(_plain(value), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _require(actual, expected, label):
    if actual != expected:
        raise ReplayError(f"{label}: registered {actual!r}, reconstructed {expected!r}")


def write_f1_run(snapshot: Snapshot, result: Mapping, directory: str | Path) -> Path:
    """Persist a completed synthetic F1 result, refusing an existing directory."""
    target = Path(directory)
    manifest = result["manifest"]
    if not manifest.get("synthetic") or manifest.get("snapshot_hash") != snapshot.content_hash:
        raise ValueError("result manifest does not identify the synthetic snapshot")
    if any(row["kind"] == "delisting_ex" for row in result["ledger"]) and manifest.get("event_schema_version") != 2:
        raise ValueError("resolved delisting requires event schema version 2")
    run_id = manifest["run_id"]
    contents = {"snapshot.json": _json(snapshot.payload) + b"\n"}
    for table in TABLES:
        contents[f"{table}.jsonl"] = b"".join(
            _json(dict(run_id=run_id, **row)) + b"\n" for row in result[table])
    schema = (DELISTING_SCHEMA_VERSION if manifest.get("event_schema_version") == 2 else
              MONTHLY_SCHEMA_VERSION if manifest.get("schema_version") == 5 else
              CONTINUOUS_SCHEMA_VERSION if manifest.get("schema_version") == 4 else
              REBALANCE_SCHEMA_VERSION if manifest.get("schema_version") == 3 else SCHEMA_VERSION)
    envelope = dict(artifact_schema_version=schema, run=manifest,
                    files={name: sha256(contents[name]).hexdigest() for name in FILES})
    contents["manifest.json"] = _json(envelope) + b"\n"
    target.mkdir(parents=True, exist_ok=False)
    for name, data in contents.items():
        (target / name).write_bytes(data)
    return target


def _load_json(data, label):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReplayError(f"{label}: duplicate key {key}")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ReplayError(f"{label}: {value}")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"{label}: invalid JSON: {exc}") from exc


def replay_f1(directory: str | Path) -> dict:
    """Verify persisted bytes and reconstruct the book without calling run_f1."""
    root = Path(directory)
    try:
        envelope = _load_json((root / "manifest.json").read_bytes(), "manifest.json")
        if envelope["artifact_schema_version"] not in (SCHEMA_VERSION, REBALANCE_SCHEMA_VERSION,
                                                         CONTINUOUS_SCHEMA_VERSION, MONTHLY_SCHEMA_VERSION,
                                                         DELISTING_SCHEMA_VERSION) or set(envelope["files"]) != set(FILES):
            raise ReplayError("manifest: unsupported schema or file set")
        run = envelope["run"]
        _require(envelope["artifact_schema_version"],
                 (DELISTING_SCHEMA_VERSION if run.get("event_schema_version") == 2 else
                  MONTHLY_SCHEMA_VERSION if run["schema_version"] == 5 else
                  CONTINUOUS_SCHEMA_VERSION if run["schema_version"] == 4 else
                  REBALANCE_SCHEMA_VERSION if run["schema_version"] == 3 else SCHEMA_VERSION),
                 "artifact schema")
        run_id = run["run_id"]
        identity = dict(run)
        del identity["run_id"]
        _require(run_id, sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "run_id")
        data = {}
        for name in FILES:
            raw = (root / name).read_bytes()
            _require(sha256(raw).hexdigest(), envelope["files"][name], f"{name} SHA-256")
            data[name] = raw
        snapshot = parse_snapshot(_load_json(data["snapshot.json"], "snapshot.json"))
        _require(snapshot.content_hash, run["snapshot_hash"], "snapshot hash")
        _require(snapshot.calendar_id, run["calendar_id"], "calendar")
        tables = {}
        for table in TABLES:
            rows = [_load_json(line, f"{table}[{index}]") for index, line in enumerate(data[f"{table}.jsonl"].splitlines())]
            for row in rows:
                _require(row.pop("run_id"), run_id, f"{table} run_id")
            tables[table] = rows
    except OSError as exc:
        raise ReplayError(f"missing or unreadable artifact: {exc.filename}") from exc
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ReplayError(f"invalid artifact structure: {exc}") from exc

    try:
        with localcontext(Context(prec=28)):
            return _reconstruct(snapshot, run, tables)
    except (InvalidOperation, StopIteration, KeyError, TypeError, IndexError) as exc:
        raise ReplayError(f"invalid replay event: {exc}") from exc


def _reconstruct(snapshot, run, tables):
    control_id = run.get("control_id")
    if control_id not in (None, "cash", "equal_weight"):
        raise ReplayError("unknown synthetic control")
    if control_id is not None:
        _require(run["model_id"], f"synthetic-f2-{control_id}-v1", "control model")
    if control_id == "cash" and any(tables[table] for table in ("orders", "order_states", "fills", "ledger")):
        raise ReplayError("cash control cannot trade or post events")
    calendar = {s["session"]: s for s in snapshot.payload["calendar"]["sessions"]}
    nav_days = [row["session"] for row in tables["nav"]]
    decision = datetime.fromisoformat(run["decision_at"].replace("Z", "+00:00"))
    expected_days = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                     if datetime.fromisoformat(s["open_at"].replace("Z", "+00:00")) > decision]
    expiry = int(run["config"]["expiry_sessions"])
    if run["schema_version"] == 5:
        windows = run["decision_windows"]
        if len(windows) < 3:
            raise ReplayError("monthly run requires at least three windows")
        _require(windows[0]["decision_at"], run["decision_at"], "first decision")
        _require(windows[0]["formation_session"], run["formation_session"], "first formation")
        expected = []
        previous_execution = None
        previous_formation = None
        previous_decision = None
        for index, window in enumerate(windows):
            window_decision = datetime.fromisoformat(window["decision_at"].replace("Z", "+00:00"))
            execution = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                         if datetime.fromisoformat(s["open_at"].replace("Z", "+00:00")) > window_decision][:expiry]
            _require(window["execution_sessions"], execution, f"window {index + 1} execution")
            if previous_execution is None:
                _require(window["bridge_sessions"], [], "first bridge")
            else:
                if window_decision <= previous_decision:
                    raise ReplayError("monthly decisions out of order")
                year, month = map(int, previous_formation[:7].split("-"))
                next_month = f"{year + (month == 12):04d}-{month % 12 + 1:02d}"
                if window["formation_session"][:7] != next_month:
                    raise ReplayError("monthly formation gap")
                bridge = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                          if previous_execution[-1] < s["session"] <= window["formation_session"]]
                _require(window["bridge_sessions"], bridge, f"window {index + 1} bridge")
                expected.extend(bridge)
            expected.extend(execution)
            previous_execution = execution
            previous_formation = window["formation_session"]
            previous_decision = window_decision
    elif run["schema_version"] in (3, 4):
        second_decision = datetime.fromisoformat(run["second_decision_at"].replace("Z", "+00:00"))
        second_days = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                       if datetime.fromisoformat(s["open_at"].replace("Z", "+00:00")) > second_decision][:expiry]
        if run["schema_version"] == 4:
            bridge = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                      if expected_days[expiry - 1] < s["session"] <= run["second_formation_session"]]
            _require(run["bridge_sessions"], bridge, "bridge sessions")
        else:
            bridge = [run["second_formation_session"]]
        expected = expected_days[:expiry] + bridge + second_days
        _require(run["decision_windows"][0]["execution_sessions"], expected_days[:expiry], "first window")
        _require(run["decision_windows"][1]["execution_sessions"], second_days, "second window")
        _require(run["decision_windows"][1]["formation_session"], run["second_formation_session"], "second formation")
    else:
        expected = expected_days[:expiry]
    _require(nav_days, expected, "NAV sessions")
    if any(row["session"] not in nav_days for row in tables["ledger"]):
        raise ReplayError("ledger event outside NAV sessions")
    if [row["session"] for row in tables["ledger"]] != sorted(row["session"] for row in tables["ledger"]):
        raise ReplayError("ledger sessions out of order")
    orders = {row["order_id"]: row for row in tables["orders"]}
    if len(orders) != len(tables["orders"]):
        raise ReplayError("duplicate order_id")
    fills = {row["fill_id"]: row for row in tables["fills"]}
    if len(fills) != len(tables["fills"]):
        raise ReplayError("duplicate fill_id")
    if len({row["event_id"] for row in tables["ledger"]}) != len(tables["ledger"]):
        raise ReplayError("duplicate ledger event_id")
    if any(row["kind"] == "delisting_ex" for row in tables["ledger"]) and run.get("event_schema_version") != 2:
        raise ReplayError("resolved delisting requires event schema version 2")
    initial = Decimal(run["config"]["initial_cash"])
    cash, positions, bases, receivables = initial, {}, {}, {}
    seen_fills, seen_actions = set(), set()
    buy_days = set()
    trade_days = set()
    filled_by_order = {}
    fills_by_order = {}
    actions = {row["action_id"]: row for row in snapshot.payload["actions"]}
    actions_by_ex = {}
    actions_by_pay = {}
    for action in actions.values():
        actions_by_ex.setdefault(action["ex_session"], []).append(action)
        if action.get("pay_session"):
            actions_by_pay.setdefault(action["pay_session"], []).append(action)
    ledger_by_day = {}
    for entry in tables["ledger"]:
        ledger_by_day.setdefault(entry["session"], []).append(entry)
    for row in tables["ledger"]:
        event_id, kind, ident, day = (row[key] for key in ("event_id", "kind", "instrument_id", "session"))
        if kind in ("buy", "sell"):
            trade_days.add(day)
            if kind == "sell" and day in buy_days:
                raise ReplayError("sale recorded after a buy in the same session")
            if kind == "buy":
                buy_days.add(day)
            if event_id in seen_fills or event_id not in fills:
                raise ReplayError(f"ledger: duplicate or unknown fill {event_id}")
            fill = fills[event_id]
            order = orders[fill["order_id"]]
            _require((ident, day), (fill["instrument_id"], fill["session"]), "fill identity")
            _require((ident, order["side"]), (order["instrument_id"], kind), "order identity")
            if kind == "sell" or "side" in fill:
                _require(fill["side"], kind, "fill side")
            _require(fill["source_key"], f"open:{ident}:{day}", "fill source")
            open_at = calendar[day]["open_at"]
            opening = next(o for o in snapshot.available("opens", datetime.fromisoformat(open_at.replace("Z", "+00:00")), session=day)
                           if o["instrument_id"] == ident)
            if not opening["tradable"] or ident not in listed_members(
                snapshot, day, as_of=datetime.fromisoformat(open_at.replace("Z", "+00:00"))):
                raise ReplayError("fill during suspended or untradable opening")
            if not (datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")) <
                    datetime.fromisoformat(open_at.replace("Z", "+00:00")) and
                    datetime.fromisoformat(order["earliest_execution_at"].replace("Z", "+00:00")) <=
                    datetime.fromisoformat(open_at.replace("Z", "+00:00")) and day <= order["expiry_session"]):
                raise ReplayError("fill outside causal order window")
            _require(fill["reference_price"], str(opening["open_price"]), "opening price")
            _require(datetime.fromisoformat(fill["input_available_at"].replace("Z", "+00:00")),
                     datetime.fromisoformat(opening["available_at"].replace("Z", "+00:00")), "opening availability")
            _require(datetime.fromisoformat(fill["executed_at"].replace("Z", "+00:00")),
                     datetime.fromisoformat(open_at.replace("Z", "+00:00")), "fill time")
            quantity = fill["quantity"]
            if type(quantity) is not int or quantity <= 0:
                raise ReplayError("fill quantity must be a positive integer")
            if quantity % int(run["config"]["lot"]) or quantity > order["capacity_shares"]:
                raise ReplayError("fill violates lot or capacity")
            fills_by_order.setdefault(order["order_id"], []).append(fill)
            filled_by_order[order["order_id"]] = filled_by_order.get(order["order_id"], 0) + quantity
            if filled_by_order[order["order_id"]] > order["quantity"]:
                raise ReplayError("fill exceeds order quantity")
            price = Decimal(fill["price"])
            reference = Decimal(fill["reference_price"])
            cost_rate = (Decimal(run["config"]["half_spread_bps"]) + Decimal(run["config"]["slippage_bps"])) / 10000
            _require(price, reference * (1 + cost_rate if kind == "buy" else 1 - cost_rate), "fill price")
            base = Decimal(fill["reference_notional"])
            notional = Decimal(fill["notional_brl"])
            spread = Decimal(fill["spread_cost"])
            slippage = Decimal(fill["slippage_cost"])
            fees = Decimal(fill["fees"])
            _require(base, _money(reference * quantity), "reference notional")
            _require(notional, _money(price * quantity), "fill notional")
            cost = notional - base if kind == "buy" else base - notional
            _require(spread, min(cost, _money(reference * quantity * Decimal(run["config"]["half_spread_bps"]) / 10000)), "spread")
            _require(slippage, cost - spread, "slippage")
            _require(fees, _money(notional * Decimal(run["config"]["fees_bps"]) / 10000), "fees")
            if kind == "buy":
                debit = Decimal(fill["cash_debit"])
                _require(debit, notional + fees, "cash debit")
                cash -= debit
                positions[ident] = positions.get(ident, 0) + quantity
                bases[ident] = bases.get(ident, Decimal(0)) + debit
                _require(Decimal(row["cash_delta"]), -debit, "buy cash delta")
                if cash < 0:
                    raise ReplayError("buy used cash before it was available")
            else:
                holding = positions.get(ident, 0)
                if not 0 < quantity <= holding:
                    raise ReplayError("sale exceeds position")
                credit = notional - fees
                removed = bases[ident] if quantity == holding else _money(bases[ident] * quantity / holding)
                _require(Decimal(fill["cash_credit"]), credit, "sale cash credit")
                _require(Decimal(fill["basis_removed"]), removed, "sale basis removed")
                _require(Decimal(fill["realized_pnl"]), credit - removed, "sale realized P&L")
                cash += credit
                positions[ident] -= quantity
                bases[ident] -= removed
                _require(Decimal(row["cash_delta"]), credit, "sell cash delta")
            seen_fills.add(event_id)
        elif kind in ("split", "dividend_ex", "unresolved_delisting", "delisting_ex"):
            if event_id in seen_actions or event_id not in actions:
                raise ReplayError(f"ledger: duplicate or unknown action {event_id}")
            if day in trade_days:
                raise ReplayError("corporate action recorded after trading")
            action = actions[event_id]
            if (datetime.fromisoformat(action["available_at"].replace("Z", "+00:00")) >
                    datetime.fromisoformat(calendar[day]["open_at"].replace("Z", "+00:00"))):
                raise ReplayError(f"late corporate action {event_id}")
            _require((ident, day), (action["instrument_id"], action["ex_session"]), "action identity")
            expected_kind = {"split": "split", "dividend": "dividend_ex",
                             "delisting": "delisting_ex" if "exit_cash_per_share" in action
                             else "unresolved_delisting"}[action["kind"]]
            _require(kind, expected_kind, "action kind")
            if kind == "split":
                updated = Decimal(positions[ident]) * Decimal(str(action["ratio"]))
                if updated != int(updated):
                    raise ReplayError("fractional split")
                positions[ident] = int(updated)
            elif kind == "dividend_ex":
                receivables[event_id] = _money(Decimal(positions[ident]) * Decimal(str(action["cash_per_share"])))
            elif kind == "delisting_ex":
                quantity = positions.get(ident, 0)
                if not quantity:
                    raise ReplayError("resolved delisting without position")
                amount = _money(Decimal(quantity) * Decimal(str(action["exit_cash_per_share"])))
                removed = bases[ident]
                _require(Decimal(row["basis_removed"]), removed, "delisting basis removed")
                _require(Decimal(row["realized_pnl"]), amount - removed, "delisting realized P&L")
                positions[ident] = 0
                bases[ident] = Decimal(0)
                receivables[event_id] = amount
            _require(Decimal(row["cash_delta"]), Decimal(0), "action cash delta")
            seen_actions.add(event_id)
        elif kind in ("dividend_pay", "delisting_pay"):
            if day in trade_days:
                raise ReplayError("payment recorded after trading")
            action_id = event_id.removesuffix("-pay")
            if action_id not in receivables:
                raise ReplayError(f"payment without receivable: {event_id}")
            _require((ident, day), (actions[action_id]["instrument_id"],
                                    actions[action_id]["pay_session"]), "payment identity")
            _require(kind, "delisting_pay" if actions[action_id]["kind"] == "delisting"
                     else "dividend_pay", "payment kind")
            amount = receivables.pop(action_id)
            cash += amount
            _require(Decimal(row["cash_delta"]), amount, "payment cash delta")
        else:
            raise ReplayError(f"unsupported ledger kind: {kind}")
        _require(row["quantity"], positions.get(ident, 0), "ledger quantity")
        _require(Decimal(row["cost_basis"]), bases.get(ident, Decimal(0)), "ledger cost basis")
        _require(Decimal(row["cash_brl"]), cash, "ledger cash")
        _require(Decimal(row["receivable_brl"]), sum(receivables.values(), Decimal(0)), "ledger receivables")
    _require(seen_fills, set(fills), "ledger fill coverage")
    cancellations = {}
    for action in actions.values():
        if action["kind"] in ("split", "delisting"):
            cancellations.setdefault(action["instrument_id"], []).append(action)
    for state in tables["order_states"]:
        order = orders[state["order_id"]]
        filled = filled_by_order.get(state["order_id"], 0)
        _require(state["instrument_id"], order["instrument_id"], "order state identity")
        _require(state["filled"], filled, "order filled")
        _require(state["remaining"], order["quantity"] - filled, "order remaining")
        expected_status, expected_reason = ("FILLED", "complete") if filled == order["quantity"] else (
            "EXPIRED", "expiry_session_reached")
        earliest = datetime.fromisoformat(order["earliest_execution_at"].replace("Z", "+00:00"))
        for action in sorted(cancellations.get(order["instrument_id"], ()),
                             key=lambda a: (a["ex_session"], a["kind"] != "split", a["action_id"])):
            ex_day = action["ex_session"]
            ex_open = datetime.fromisoformat(calendar[ex_day]["open_at"].replace("Z", "+00:00"))
            available = datetime.fromisoformat(action["available_at"].replace("Z", "+00:00"))
            if ex_day not in nav_days or ex_open < earliest or ex_day > order["expiry_session"]:
                continue
            order_fills = fills_by_order.get(order["order_id"], ())
            before = sum(f["quantity"] for f in order_fills if f["session"] < ex_day)
            if before < order["quantity"]:
                if available > ex_open:
                    raise ReplayError(f"late corporate action {action['action_id']}")
                if any(f["session"] >= ex_day for f in order_fills):
                    raise ReplayError("fill after order cancellation")
                expected_status, expected_reason = "CANCELLED", f"{action['kind']}_requires_new_order"
                break
        _require(state["status"], expected_status, "terminal order status")
        _require(state["reason"], expected_reason, "terminal order reason")
    _require({s["order_id"] for s in tables["order_states"]}, set(orders), "order state coverage")
    _require(len(tables["order_states"]), len(orders), "order state count")
    results = []
    # Reapply ledger events at each session boundary to reconstruct historical NAV.
    cash, positions, receivables = initial, {}, {}
    historical_unresolved = set()
    for row in tables["nav"]:
        day = row["session"]
        daily_events = ledger_by_day.get(day, ())
        daily_ids = {entry["event_id"] for entry in daily_events}
        open_at = datetime.fromisoformat(calendar[day]["open_at"].replace("Z", "+00:00"))
        valued_at = datetime.fromisoformat(row["valued_at"].replace("Z", "+00:00"))
        for action in actions_by_ex.get(day, ()):
            action_id = action["action_id"]
            available = datetime.fromisoformat(action["available_at"].replace("Z", "+00:00"))
            if positions.get(action["instrument_id"], 0):
                if available > open_at:
                    raise ReplayError(f"late corporate action {action_id}")
                if action_id not in daily_ids:
                    raise ReplayError(f"missing corporate action {action_id}")
        for action in actions_by_pay.get(day, ()):
            action_id = action["action_id"]
            available = datetime.fromisoformat(action["available_at"].replace("Z", "+00:00"))
            if action_id in receivables and available <= valued_at:
                if f"{action_id}-pay" not in daily_ids:
                    raise ReplayError(f"missing dividend payment {action_id}")
        close = datetime.fromisoformat(calendar[day]["close_at"].replace("Z", "+00:00"))
        _require(datetime.fromisoformat(row["valued_at"].replace("Z", "+00:00")),
                 close + timedelta(minutes=int(run["config"]["mark_delay_minutes"])), "NAV time")
        for entry in daily_events:
            ident, kind, event_id = entry["instrument_id"], entry["kind"], entry["event_id"]
            if kind == "buy":
                fill = fills[event_id]
                cash -= Decimal(fill["cash_debit"])
                positions[ident] = positions.get(ident, 0) + fill["quantity"]
            elif kind == "sell":
                fill = fills[event_id]
                cash += Decimal(fill["cash_credit"])
                positions[ident] -= fill["quantity"]
            elif kind == "split":
                positions[ident] = int(Decimal(positions[ident]) * Decimal(str(actions[event_id]["ratio"])))
            elif kind == "dividend_ex":
                receivables[event_id] = _money(Decimal(positions[ident]) * Decimal(str(actions[event_id]["cash_per_share"])))
            elif kind == "delisting_ex":
                receivables[event_id] = _money(Decimal(positions[ident]) *
                                               Decimal(str(actions[event_id]["exit_cash_per_share"])))
                positions[ident] = 0
            elif kind == "unresolved_delisting":
                historical_unresolved.add(ident)
            elif kind in ("dividend_pay", "delisting_pay"):
                cash += receivables.pop(event_id.removesuffix("-pay"))
        closes = {bar["instrument_id"]: bar for bar in snapshot.available("bars", valued_at, session=day)}
        missing = sorted(ident for ident, quantity in positions.items()
                         if quantity and (ident not in closes or ident in historical_unresolved))
        marks = {ident: {"quantity": quantity, "price": str(closes[ident]["close"]), "source_key": f"bar:{ident}:{day}"}
                 for ident, quantity in positions.items() if quantity and ident in closes and ident not in missing}
        value = None if missing else _money(sum((Decimal(m["price"]) * m["quantity"] for m in marks.values()), Decimal(0)))
        due = sum(receivables.values(), Decimal(0))
        expected = {"session": day, "valued_at": row["valued_at"], "status": "NAV_INCOMPLETO" if missing else "COMPLETE",
                    "cash_brl": format(cash, "f"), "receivable_brl": format(due, "f"),
                    "positions_value_brl": None if missing else format(value, "f"),
                    "nav_brl": None if missing else format(_money(cash + due + value), "f"),
                    "missing_marks": missing, "marks": marks}
        _require(row, expected, f"NAV {day}")
        results.append(expected)
    _require(cash, Decimal(tables["ledger"][-1]["cash_brl"]) if tables["ledger"] else initial, "final cash")
    return {"run_id": run["run_id"], "control_id": run.get("control_id"),
            "cash_brl": cash, "positions": positions,
            "cost_basis": bases, "receivables": receivables, "nav": tuple(results)}
