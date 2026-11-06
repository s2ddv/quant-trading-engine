"""Causal audit of persisted synthetic F1 runs."""

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from qtre.data.snapshot import load_snapshot
from qtre.reporting import ReplayError, _json, _load_json, replay_f1
from qtre.signals import momentum_12_2

AUDIT_SCHEMA_VERSION = 1


def _instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp has no timezone")
    return parsed


def _source(row, when, label):
    for field in ("source_id", "source_version", "snapshot_id", "observed_at", "available_at", "ingested_at"):
        if not row.get(field):
            raise ValueError(f"{label}: missing provenance {field}")
    if _instant(row["available_at"]) > when:
        raise ValueError(f"{label}: source available after use")


def audit_f1_run(directory: str | Path) -> dict:
    """Audit F1 inputs and replay, writing a deterministic, versioned report."""
    root = Path(directory)
    manifest_bytes = (root / "manifest.json").read_bytes()
    envelope = _load_json(manifest_bytes, "manifest.json")
    run_id = envelope["run"]["run_id"]
    report = {"audit_schema_version": AUDIT_SCHEMA_VERSION, "run_id": run_id,
              "manifest_sha256": sha256(manifest_bytes).hexdigest(),
              "artifact_hashes": envelope["files"], "status": "INVALID", "findings": [],
              "checks": ["replay", "decision_inputs", "order_before_fill",
                         "source_provenance", "nav_completeness"]}
    if envelope["run"].get("control_id") is not None:
        report["control_id"] = envelope["run"]["control_id"]
        report["checks"].append("control_targets")
    try:
        rebuilt = replay_f1(root)
        snapshot = load_snapshot(root / "snapshot.json")
        bars = {f"bar:{r['instrument_id']}:{r['session']}": r for r in snapshot.payload["bars"]}
        opens = {f"open:{r['instrument_id']}:{r['session']}": r for r in snapshot.payload["opens"]}
        memberships = {f"membership:{r['instrument_id']}:{r['valid_from']}": r
                       for r in snapshot.payload["memberships"]}
        actions = {f"action:{r['action_id']}": r for r in snapshot.payload["actions"]}
        sources = {**bars, **memberships, **actions}
        orders = [_load_json(line, "orders.jsonl") for line in (root / "orders.jsonl").read_bytes().splitlines()]
        fills = [_load_json(line, "fills.jsonl") for line in (root / "fills.jsonl").read_bytes().splitlines()]
        nav = [_load_json(line, "nav.jsonl") for line in (root / "nav.jsonl").read_bytes().splitlines()]
        windows = envelope["run"].get("decision_windows") or [
            {"decision_at": envelope["run"]["decision_at"],
             "formation_session": envelope["run"]["formation_session"]}]
        decisions = {_instant(w["decision_at"]): w for w in windows}
        if envelope["run"].get("control_id") == "equal_weight":
            cap = Decimal(envelope["run"]["config"]["max_name_weight"])
            for decision_at, window in decisions.items():
                eligible = {s.instrument_id for s in momentum_12_2(
                    snapshot, decision_at=decision_at,
                    formation_session=window["formation_session"]) if s.eligible}
                weight = min(Decimal(1) / len(eligible), cap) if eligible else Decimal(0)
                for order in orders:
                    if _instant(order["created_at"]) != decision_at:
                        continue
                    expected = weight if order["instrument_id"] in eligible else Decimal(0)
                    if Decimal(order["target_weight"]) != expected:
                        raise ValueError(f"order {order['order_id']}: equal weight target mismatch")
        by_order = {o["order_id"]: o for o in orders}
        for order in orders:
            label = f"order {order['order_id']}"
            created = _instant(order["created_at"])
            window = decisions.get(created)
            if window is None or order["reference_session"] != window["formation_session"]:
                raise ValueError(f"{label}: decision or formation mismatch")
            if created >= _instant(order["earliest_execution_at"]):
                raise ValueError(f"{label}: earliest fill is not after creation")
            keys = order["input_keys"]
            reference = f"bar:{order['instrument_id']}:{order['reference_session']}"
            if not keys or len(set(keys)) != len(keys) or reference not in keys:
                raise ValueError(f"{label}: missing or duplicate input provenance")
            for key in keys:
                row = sources.get(key)
                if row is None or row["instrument_id"] != order["instrument_id"]:
                    raise ValueError(f"{label}: unknown or unrelated input {key}")
                _source(row, created, f"{label} input {key}")
            if Decimal(str(bars[reference]["close"])) != Decimal(str(order["reference_price"])):
                raise ValueError(f"{label}: reference price mismatch")
        for fill in fills:
            label = f"fill {fill['fill_id']}"
            order = by_order[fill["order_id"]]
            executed = _instant(fill["executed_at"])
            if _instant(order["created_at"]) >= executed:
                raise ValueError(f"{label}: order was not created before fill")
            key = fill["source_key"]
            source = opens.get(key)
            if source is None:
                raise ValueError(f"{label}: opening source missing")
            _source(source, executed, label)
            if _instant(fill["input_available_at"]) != _instant(source["available_at"]):
                raise ValueError(f"{label}: opening availability mismatch")
        for mark in nav:
            valued = _instant(mark["valued_at"])
            for ident, item in mark["marks"].items():
                key = item["source_key"]
                row = bars.get(key)
                if key != f"bar:{ident}:{mark['session']}" or row is None:
                    raise ValueError(f"NAV {mark['session']}: mark source mismatch")
                _source(row, valued, f"NAV {mark['session']}")
            incomplete = mark["status"] == "NAV_INCOMPLETO"
            if incomplete != (mark["nav_brl"] is None and mark["positions_value_brl"] is None):
                raise ValueError(f"NAV {mark['session']}: incomplete value policy violated")
        if rebuilt["run_id"] != run_id:
            raise ValueError("replay identity mismatch")
        report["status"] = "VALID"
        report["counts"] = {"orders": len(orders), "fills": len(fills), "nav": len(nav),
                            "incomplete_nav": sum(r["status"] == "NAV_INCOMPLETO" for r in nav),
                            "decisions": len(windows)}
    except (ReplayError, ValueError, KeyError, TypeError, OSError) as exc:
        report["status"] = "INVALID"
        report.pop("counts", None)
        report["findings"].append(str(exc))
    output = _json(report) + b"\n"
    path = root / "audit.json"
    try:
        with path.open("xb") as stream:
            stream.write(output)
    except FileExistsError:
        if path.read_bytes() != output:
            raise ValueError("existing audit.json differs from current audit")
    return report
