"""F0 snapshot parser and deterministic content identity.

The synthetic calendar is supplied by the fixture. It does not assert any B3
holiday, auction, settlement, or trading-hour rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from zoneinfo import ZoneInfo


class SnapshotError(ValueError):
    """An input snapshot violates a versioned F0 contract."""


def _fail(path: str, reason: str) -> None:
    raise SnapshotError(f"{path}: {reason}")


def _object(value: Any, path: str, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "expected object")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing or extra:
        _fail(path, f"missing={sorted(missing)}, unknown={sorted(extra)}")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "expected non-empty string")
    return value


def _date(value: Any, path: str) -> date:
    if not isinstance(value, str):
        _fail(path, "expected ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        _fail(path, "invalid ISO date")
    if parsed.isoformat() != value:
        _fail(path, "date must be canonical YYYY-MM-DD")
    return parsed


def _instant(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        _fail(path, "expected ISO timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(path, "invalid ISO timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(path, "timezone is required")
    return parsed.astimezone(timezone.utc)


def _money(value: Any, path: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        _fail(path, "expected finite decimal")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        _fail(path, "expected finite decimal")
    if not result.is_finite() or result < 0 or (positive and result == 0):
        _fail(path, "expected finite non-negative decimal" if not positive else "expected finite positive decimal")
    return result


def _integer(value: Any, path: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (positive and value == 0):
        _fail(path, "expected non-negative integer" if not positive else "expected positive integer")
    return value


def _provenance(row: dict[str, Any], path: str, snapshot_id: str, as_of: datetime) -> None:
    for key in ("source_id", "source_version"):
        _string(row[key], f"{path}.{key}")
    if row["snapshot_id"] != snapshot_id:
        _fail(f"{path}.snapshot_id", "does not match snapshot")
    observed = _instant(row["observed_at"], f"{path}.observed_at")
    available = _instant(row["available_at"], f"{path}.available_at")
    ingested = _instant(row["ingested_at"], f"{path}.ingested_at")
    if observed > available:
        _fail(path, "observed_at is after available_at")
    if available > as_of or ingested > as_of:
        _fail(path, "future data relative to snapshot as_of")
    if ingested < available:
        _fail(path, "ingested_at is before available_at")


_COMMON = {"source_id", "source_version", "snapshot_id", "observed_at", "available_at", "ingested_at"}


def _unique(rows: list[dict[str, Any]], fields: tuple[str, ...], path: str) -> None:
    seen: set[tuple[Any, ...]] = set()
    for n, row in enumerate(rows):
        key = tuple(row[field] for field in fields)
        if key in seen:
            _fail(f"{path}[{n}]", f"duplicate {fields}: {key}")
        seen.add(key)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    as_of: datetime
    calendar_id: str
    content_hash: str
    payload: Mapping[str, Any]

    def available(self, collection: str, as_of: datetime) -> tuple[Mapping[str, Any], ...]:
        """Return source records available by a decision instant; never mutate them."""
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise SnapshotError("as_of: timezone is required")
        if as_of > self.as_of:
            raise SnapshotError("as_of: later than frozen snapshot")
        if collection not in ("bars", "opens", "actions", "memberships", "symbols"):
            raise SnapshotError(f"unknown collection: {collection}")
        return tuple(row for row in self.payload[collection] if _instant(row["available_at"], "available_at") <= as_of)


def parse_snapshot(payload: Any) -> Snapshot:
    root = _object(payload, "snapshot", {"schema_version", "snapshot_id", "as_of", "calendar", "bars", "opens", "actions", "memberships", "symbols"})
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        _fail("schema_version", "expected version 1")
    snapshot_id = _string(root["snapshot_id"], "snapshot_id")
    as_of = _instant(root["as_of"], "as_of")
    cal = _object(root["calendar"], "calendar", {"calendar_id", "timezone", "sessions"})
    calendar_id = _string(cal["calendar_id"], "calendar.calendar_id")
    if cal["timezone"] != "America/Sao_Paulo":
        _fail("calendar.timezone", "expected America/Sao_Paulo")
    if not isinstance(cal["sessions"], list) or not cal["sessions"]:
        _fail("calendar.sessions", "expected non-empty list")
    sessions: set[str] = set()
    prev: date | None = None
    prev_close: datetime | None = None
    for n, row in enumerate(cal["sessions"]):
        path = f"calendar.sessions[{n}]"
        _object(row, path, {"session", "open_at", "close_at"})
        day = _date(row["session"], f"{path}.session")
        opened = _instant(row["open_at"], f"{path}.open_at")
        closed = _instant(row["close_at"], f"{path}.close_at")
        if prev is not None and day <= prev:
            _fail(path, "sessions must be strictly increasing")
        if opened >= closed or closed > as_of:
            _fail(path, "invalid or future session clock")
        local_zone = ZoneInfo("America/Sao_Paulo")
        if opened.astimezone(local_zone).date() != day or closed.astimezone(local_zone).date() != day:
            _fail(path, "session clock must fall on local session date")
        if prev_close is not None and opened <= prev_close:
            _fail(path, "session clocks overlap")
        sessions.add(row["session"])
        prev = day
        prev_close = closed

    for collection in ("bars", "opens", "actions", "memberships", "symbols"):
        if not isinstance(root[collection], list):
            _fail(collection, "expected list")
        for n, row in enumerate(root[collection]):
            path = f"{collection}[{n}]"
            required = {
                "bars": {"instrument_id", "session", "open", "high", "low", "close", "volume_shares", "volume_brl", "currency", "adjustment_basis"},
                "opens": {"instrument_id", "session", "open_price", "currency", "tradable"},
                "actions": {"action_id", "instrument_id", "kind", "announced_at", "ex_session"},
                "memberships": {"instrument_id", "valid_from", "valid_to", "status", "reason"},
                "symbols": {"instrument_id", "ticker", "valid_from", "valid_to"},
            }[collection] | _COMMON
            optional = {"actions": {"record_session", "pay_session", "ratio", "cash_per_share", "successor_id"}}.get(collection, set())
            _object(row, path, required, optional)
            _provenance(row, path, snapshot_id, as_of)
            _string(row["instrument_id"], f"{path}.instrument_id")
            if collection in ("bars", "opens"):
                if row["session"] not in sessions:
                    _fail(f"{path}.session", "not in calendar")
                if row["currency"] != "BRL":
                    _fail(f"{path}.currency", "expected BRL")
            if collection == "bars":
                prices = {key: _money(row[key], f"{path}.{key}", positive=True) for key in ("open", "high", "low", "close")}
                if prices["high"] < max(prices["open"], prices["close"], prices["low"]) or prices["low"] > min(prices["open"], prices["close"]):
                    _fail(path, "inconsistent OHLC")
                _integer(row["volume_shares"], f"{path}.volume_shares")
                _money(row["volume_brl"], f"{path}.volume_brl")
                if row["adjustment_basis"] != "raw":
                    _fail(f"{path}.adjustment_basis", "F0 execution bars must be raw")
                close_at = _instant(next(s["close_at"] for s in cal["sessions"] if s["session"] == row["session"]), "close_at")
                if _instant(row["observed_at"], "observed_at") < close_at:
                    _fail(path, "complete bar observed before session close")
                if _instant(row["available_at"], "available_at") < close_at:
                    _fail(path, "complete bar available before session close")
            elif collection == "opens":
                _money(row["open_price"], f"{path}.open_price", positive=True)
                if type(row["tradable"]) is not bool:
                    _fail(f"{path}.tradable", "expected boolean")
                open_at = _instant(next(s["open_at"] for s in cal["sessions"] if s["session"] == row["session"]), "open_at")
                if _instant(row["available_at"], "available_at") < open_at:
                    _fail(path, "open event available before session open")
            elif collection == "actions":
                _string(row["action_id"], f"{path}.action_id")
                if row["kind"] not in ("split", "dividend", "delisting"):
                    _fail(f"{path}.kind", "unsupported action")
                announced = _instant(row["announced_at"], f"{path}.announced_at")
                if announced > _instant(row["available_at"], "available_at"):
                    _fail(path, "announcement after availability")
                for key in ("ex_session", "record_session", "pay_session"):
                    if key in row and row[key] is not None and row[key] not in sessions:
                        _fail(f"{path}.{key}", "not in calendar")
                if row["kind"] == "split":
                    _money(row.get("ratio"), f"{path}.ratio", positive=True)
                if row["kind"] == "dividend":
                    _money(row.get("cash_per_share"), f"{path}.cash_per_share")
                    if not row.get("pay_session"):
                        _fail(path, "dividend requires pay_session")
            else:
                start = _date(row["valid_from"], f"{path}.valid_from")
                end = _date(row["valid_to"], f"{path}.valid_to") if row["valid_to"] is not None else None
                if end is not None and end < start:
                    _fail(path, "valid_to before valid_from")
                if collection == "memberships":
                    if row["status"] not in ("listed", "suspended", "delisted"):
                        _fail(path, "invalid membership status")
                    _string(row["reason"], f"{path}.reason")
                else:
                    _string(row["ticker"], f"{path}.ticker")

    _unique(root["bars"], ("instrument_id", "session"), "bars")
    _unique(root["opens"], ("instrument_id", "session"), "opens")
    _unique(root["actions"], ("action_id",), "actions")
    for collection in ("memberships", "symbols"):
        by_id: dict[str, list[dict[str, Any]]] = {}
        for row in root[collection]:
            by_id.setdefault(row["instrument_id"], []).append(row)
        for instrument_id, rows in by_id.items():
            ordered = sorted(rows, key=lambda row: row["valid_from"])
            for left, right in zip(ordered, ordered[1:]):
                if left["valid_to"] is None or left["valid_to"] >= right["valid_from"]:
                    _fail(collection, f"overlapping intervals for {instrument_id}")

    canonical = _canonical(root)
    return Snapshot(snapshot_id, as_of, calendar_id, sha256(canonical).hexdigest(), _freeze(json.loads(canonical)))


def load_snapshot(path: str | Path) -> Snapshot:
    def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(str(path), f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def no_nonfinite(token: str) -> None:
        _fail(str(path), f"non-finite JSON number: {token}")

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys, parse_constant=no_nonfinite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"{path}: cannot load snapshot: {exc}") from exc
    return parse_snapshot(data)
