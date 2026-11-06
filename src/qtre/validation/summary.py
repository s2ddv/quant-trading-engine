"""Descriptive F2 summary of an independently replayed synthetic run."""

from decimal import Decimal
from pathlib import Path

from qtre.reporting import _load_json, replay_f1


def summarize_f1_run(directory: str | Path) -> dict:
    """Report observable mechanics; omit returns if any NAV mark is incomplete."""
    root = Path(directory)
    replay_f1(root)
    envelope = _load_json((root / "manifest.json").read_bytes(), "manifest.json")
    tables = {}
    for name in ("orders", "fills", "nav"):
        tables[name] = [_load_json(line, f"{name}.jsonl")
                        for line in (root / f"{name}.jsonl").read_bytes().splitlines()]
    orders, fills, nav = (tables[name] for name in ("orders", "fills", "nav"))
    incomplete = [row["session"] for row in nav if row["status"] != "COMPLETE"]
    costs = {key: sum((Decimal(str(row[key])) for row in fills), Decimal(0))
             for key in ("spread_cost", "slippage_cost", "fees")}
    costs["total"] = sum(costs.values(), Decimal(0))
    first = Decimal(str(nav[0]["nav_brl"])) if nav and nav[0]["nav_brl"] is not None else None
    last = Decimal(str(nav[-1]["nav_brl"])) if nav and nav[-1]["nav_brl"] is not None else None
    return {
        "summary_schema_version": 1,
        "run_id": envelope["run"]["run_id"],
        "synthetic": envelope["run"]["synthetic"],
        "decisions": len(envelope["run"].get("decision_windows") or [1]),
        "orders": len(orders),
        "fills": len(fills),
        "sessions": len(nav),
        "incomplete_sessions": incomplete,
        "final_cash_brl": Decimal(str(nav[-1]["cash_brl"])) if nav else None,
        "costs_brl": costs,
        "cumulative_return": (last / first - 1) if first and last is not None and not incomplete else None,
        "return_status": "UNAVAILABLE_INCOMPLETE_NAV" if incomplete else
                         "AVAILABLE_SYNTHETIC" if first and last is not None else "UNAVAILABLE_NO_NAV",
    }
