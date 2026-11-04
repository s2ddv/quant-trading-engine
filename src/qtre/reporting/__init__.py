"""Versioned F1 artifacts and independent synthetic book replay."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from hashlib import sha256
import json
from pathlib import Path

from qtre.data.snapshot import Snapshot, load_snapshot


FILES = ("snapshot.json", "orders.jsonl", "order_states.jsonl", "fills.jsonl", "ledger.jsonl", "nav.jsonl")
TABLES = ("orders", "order_states", "fills", "ledger", "nav")
SCHEMA_VERSION = 1
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
    run_id = manifest["run_id"]
    contents = {"snapshot.json": _json(snapshot.payload) + b"\n"}
    for table in TABLES:
        contents[f"{table}.jsonl"] = b"".join(
            _json(dict(run_id=run_id, **row)) + b"\n" for row in result[table])
    envelope = dict(artifact_schema_version=SCHEMA_VERSION, run=manifest,
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
        if envelope["artifact_schema_version"] != SCHEMA_VERSION or set(envelope["files"]) != set(FILES):
            raise ReplayError("manifest: unsupported schema or file set")
        run = envelope["run"]
        run_id = run["run_id"]
        identity = dict(run)
        del identity["run_id"]
        _require(run_id, sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "run_id")
        data = {}
        for name in FILES:
            raw = (root / name).read_bytes()
            _require(sha256(raw).hexdigest(), envelope["files"][name], f"{name} SHA-256")
            data[name] = raw
        snapshot = load_snapshot(root / "snapshot.json")
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
    calendar = {s["session"]: s for s in snapshot.payload["calendar"]["sessions"]}
    nav_days = [row["session"] for row in tables["nav"]]
    decision = datetime.fromisoformat(run["decision_at"].replace("Z", "+00:00"))
    expected_days = [s["session"] for s in snapshot.payload["calendar"]["sessions"]
                     if datetime.fromisoformat(s["open_at"].replace("Z", "+00:00")) > decision]
    _require(nav_days, expected_days[:int(run["config"]["expiry_sessions"])], "NAV sessions")
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
    initial = Decimal(run["config"]["initial_cash"])
    cash, positions, bases, receivables = initial, {}, {}, {}
    seen_fills, seen_actions = set(), set()
    unresolved = set()
    actions = {row["action_id"]: row for row in snapshot.payload["actions"]}
    for row in tables["ledger"]:
        event_id, kind, ident, day = (row[key] for key in ("event_id", "kind", "instrument_id", "session"))
        if kind == "buy":
            if event_id in seen_fills or event_id not in fills:
                raise ReplayError(f"ledger: duplicate or unknown fill {event_id}")
            fill = fills[event_id]
            order = orders[fill["order_id"]]
            _require((ident, day), (fill["instrument_id"], fill["session"]), "fill identity")
            _require((ident, order["side"]), (order["instrument_id"], "buy"), "order identity")
            _require(fill["source_key"], f"open:{ident}:{day}", "fill source")
            open_at = next(s["open_at"] for s in snapshot.payload["calendar"]["sessions"] if s["session"] == day)
            opening = next(o for o in snapshot.available("opens", datetime.fromisoformat(open_at.replace("Z", "+00:00")))
                           if o["instrument_id"] == ident and o["session"] == day)
            _require(fill["reference_price"], str(opening["open_price"]), "opening price")
            _require(datetime.fromisoformat(fill["input_available_at"].replace("Z", "+00:00")),
                     datetime.fromisoformat(opening["available_at"].replace("Z", "+00:00")), "opening availability")
            _require(datetime.fromisoformat(fill["executed_at"].replace("Z", "+00:00")),
                     datetime.fromisoformat(open_at.replace("Z", "+00:00")), "fill time")
            quantity = fill["quantity"]
            if type(quantity) is not int or quantity <= 0:
                raise ReplayError("fill quantity must be a positive integer")
            price = Decimal(fill["price"])
            reference = Decimal(fill["reference_price"])
            _require(price, reference * (1 + (Decimal(run["config"]["half_spread_bps"]) + Decimal(run["config"]["slippage_bps"])) / 10000), "fill price")
            base = Decimal(fill["reference_notional"])
            notional = Decimal(fill["notional_brl"])
            spread = Decimal(fill["spread_cost"])
            slippage = Decimal(fill["slippage_cost"])
            fees = Decimal(fill["fees"])
            debit = Decimal(fill["cash_debit"])
            _require(base, _money(reference * quantity), "reference notional")
            _require(notional, _money(price * quantity), "fill notional")
            _require(spread, min(notional - base, _money(reference * quantity * Decimal(run["config"]["half_spread_bps"]) / 10000)), "spread")
            _require(slippage, notional - base - spread, "slippage")
            _require(fees, _money(notional * Decimal(run["config"]["fees_bps"]) / 10000), "fees")
            _require(debit, notional + fees, "cash debit")
            cash -= debit
            positions[ident] = positions.get(ident, 0) + quantity
            bases[ident] = bases.get(ident, Decimal(0)) + debit
            _require(Decimal(row["cash_delta"]), -debit, "buy cash delta")
            seen_fills.add(event_id)
        elif kind in ("split", "dividend_ex", "unresolved_delisting"):
            if event_id in seen_actions or event_id not in actions:
                raise ReplayError(f"ledger: duplicate or unknown action {event_id}")
            action = actions[event_id]
            _require((ident, day), (action["instrument_id"], action["ex_session"]), "action identity")
            _require(kind, {"split": "split", "dividend": "dividend_ex", "delisting": "unresolved_delisting"}[action["kind"]], "action kind")
            if kind == "split":
                updated = Decimal(positions[ident]) * Decimal(str(action["ratio"]))
                if updated != int(updated):
                    raise ReplayError("fractional split")
                positions[ident] = int(updated)
            elif kind == "dividend_ex":
                receivables[event_id] = _money(Decimal(positions[ident]) * Decimal(str(action["cash_per_share"])))
            else:
                unresolved.add(ident)
            _require(Decimal(row["cash_delta"]), Decimal(0), "action cash delta")
            seen_actions.add(event_id)
        elif kind == "dividend_pay":
            action_id = event_id.removesuffix("-pay")
            if action_id not in receivables:
                raise ReplayError(f"payment without receivable: {event_id}")
            _require(day, actions[action_id]["pay_session"], "payment session")
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
    for state in tables["order_states"]:
        order = orders[state["order_id"]]
        filled = sum(f["quantity"] for f in fills.values() if f["order_id"] == state["order_id"])
        _require(state["filled"], filled, "order filled")
        _require(state["remaining"], order["quantity"] - filled, "order remaining")
        if state["status"] not in ("FILLED", "EXPIRED", "CANCELLED"):
            raise ReplayError("invalid terminal order status")
        if state["status"] == "FILLED" and state["remaining"] != 0:
            raise ReplayError("filled order has remaining quantity")
    _require({s["order_id"] for s in tables["order_states"]}, set(orders), "order state coverage")
    _require(len(tables["order_states"]), len(orders), "order state count")
    results = []
    # Reapply ledger events at each session boundary to reconstruct historical NAV.
    cash, positions, receivables = initial, {}, {}
    for row in tables["nav"]:
        day = row["session"]
        close = datetime.fromisoformat(calendar[day]["close_at"].replace("Z", "+00:00"))
        _require(datetime.fromisoformat(row["valued_at"].replace("Z", "+00:00")),
                 close + timedelta(minutes=int(run["config"]["mark_delay_minutes"])), "NAV time")
        for entry in (e for e in tables["ledger"] if e["session"] == day):
            ident, kind, event_id = entry["instrument_id"], entry["kind"], entry["event_id"]
            if kind == "buy":
                fill = fills[event_id]
                cash -= Decimal(fill["cash_debit"])
                positions[ident] = positions.get(ident, 0) + fill["quantity"]
            elif kind == "split":
                positions[ident] = int(Decimal(positions[ident]) * Decimal(str(actions[event_id]["ratio"])))
            elif kind == "dividend_ex":
                receivables[event_id] = _money(Decimal(positions[ident]) * Decimal(str(actions[event_id]["cash_per_share"])))
            elif kind == "dividend_pay":
                cash += receivables.pop(event_id.removesuffix("-pay"))
        valued_at = datetime.fromisoformat(row["valued_at"].replace("Z", "+00:00"))
        closes = {bar["instrument_id"]: bar for bar in snapshot.available("bars", valued_at) if bar["session"] == day}
        missing = sorted(ident for ident, quantity in positions.items() if quantity and (ident not in closes or ident in unresolved and any(e["session"] <= day and e["kind"] == "unresolved_delisting" and e["instrument_id"] == ident for e in tables["ledger"])))
        marks = {ident: {"quantity": quantity, "price": str(closes[ident]["close"]), "source_key": f"bar:{ident}:{day}"}
                 for ident, quantity in positions.items() if ident in closes and ident not in missing}
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
    return {"run_id": run["run_id"], "cash_brl": cash, "positions": positions,
            "receivables": receivables, "nav": tuple(results)}
