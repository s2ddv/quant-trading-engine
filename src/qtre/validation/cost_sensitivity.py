"""Pre-registered synthetic F2 cost scenarios and conditional comparisons."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from qtre.backtest import F1Config, run_f1_monthly, run_f2_control
from qtre.reporting import _json, _load_json, replay_f1, write_f1_run
from qtre.validation import audit_f1_run


SCENARIOS = (("zero", 0, 0, 0), ("base", 5, 5, 5), ("high", 15, 15, 10))
STRATEGIES = ("momentum", "equal_weight", "cash")


def _rows(root, table):
    return [_load_json(line, f"{table}.jsonl")
            for line in (root / f"{table}.jsonl").read_bytes().splitlines()]


def _signature(rows, fields):
    return [tuple(row[field] for field in fields) for row in rows]


def _differences(left, right, key, fields):
    earlier = {row[key]: tuple(row[field] for field in fields) for row in left}
    later = {row[key]: tuple(row[field] for field in fields) for row in right}
    return [{"id": ident, "earlier": earlier.get(ident), "later": later.get(ident)}
            for ident in sorted(earlier.keys() | later.keys())
            if earlier.get(ident) != later.get(ident)]


def _report_run(root):
    replay = replay_f1(root)
    audit = audit_f1_run(root)
    if audit["status"] != "VALID":
        raise ValueError(f"invalid audit: {root}: {audit['findings']}")
    manifest = _load_json((root / "manifest.json").read_bytes(), "manifest.json")["run"]
    orders, fills, nav = (_rows(root, name) for name in ("orders", "fills", "nav"))
    costs = {name: sum((Decimal(row[name]) for row in fills), Decimal(0))
             for name in ("spread_cost", "slippage_cost", "fees")}
    costs["total"] = sum(costs.values(), Decimal(0))
    reference = sum((Decimal(row["reference_notional"]) for row in fills), Decimal(0))
    costs_bps = {name: (value * 10000 / reference if reference else None)
                 for name, value in costs.items()}
    last = nav[-1]
    cash = Decimal(last["cash_brl"])
    receivable = Decimal(last["receivable_brl"])
    if cash != replay["cash_brl"] or cash != Decimal(replay["nav"][-1]["cash_brl"]):
        raise ValueError("final cash reconciliation failed")
    if last["nav_brl"] is not None:
        positions_value = Decimal(last["positions_value_brl"])
        if cash + receivable + positions_value != Decimal(last["nav_brl"]):
            raise ValueError("final NAV reconciliation failed")
    else:
        positions_value = None
    incomplete = [row["session"] for row in nav if row["status"] == "NAV_INCOMPLETO"]
    return {
        "run_id": manifest["run_id"], "config": manifest["config"],
        "audit_status": audit["status"], "decisions": len(manifest["decision_windows"]),
        "sessions": len(nav), "orders": len(orders), "fills": len(fills),
        "costs_brl": costs, "costs_bps": costs_bps,
        "final_cash_brl": cash, "final_receivable_brl": receivable,
        "final_positions": replay["positions"], "final_cost_basis": replay["cost_basis"],
        "final_positions_value_brl": positions_value,
        "final_nav_brl": Decimal(last["nav_brl"]) if last["nav_brl"] is not None else None,
        "incomplete_sessions": incomplete,
        "complete_series_return": None if incomplete else
            Decimal(nav[-1]["nav_brl"]) / Decimal(nav[0]["nav_brl"]) - 1,
        "return_status": "UNAVAILABLE_INCOMPLETE_NAV" if incomplete else "AVAILABLE_SYNTHETIC",
    }


def compare_pair(left_root, right_root, *, raise_on_fail=True):
    """Only assert cost and NAV monotonicity for identical fill schedules and sizes."""
    left_root, right_root = Path(left_root), Path(right_root)
    left_orders, right_orders = (_rows(root, "orders") for root in (left_root, right_root))
    left_fills, right_fills = (_rows(root, "fills") for root in (left_root, right_root))
    left_nav, right_nav = (_rows(root, "nav") for root in (left_root, right_root))
    order_fields = ("order_id", "created_at", "earliest_execution_at", "side", "instrument_id", "quantity")
    fill_fields = ("order_id", "session", "executed_at", "quantity")
    same_orders = _signature(left_orders, order_fields) == _signature(right_orders, order_fields)
    same_fills = _signature(left_fills, fill_fields) == _signature(right_fills, fill_fields)
    same_nav_schedule = _signature(left_nav, ("session", "status")) == _signature(right_nav, ("session", "status"))
    result = {"orders_identical": same_orders, "fills_identical": same_fills,
              "nav_schedule_identical": same_nav_schedule,
              "order_count_delta": len(right_orders) - len(left_orders),
              "fill_count_delta": len(right_fills) - len(left_fills),
              "order_differences": _differences(left_orders, right_orders, "order_id", order_fields[1:]),
              "fill_differences": _differences(left_fills, right_fills, "fill_id", fill_fields[1:])}
    if not (same_fills and same_nav_schedule):
        result["monotonicity"] = "NOT_COMPARABLE_EXECUTION_CHANGED"
        return result
    left_cost = sum((Decimal(row[key]) for row in left_fills
                     for key in ("spread_cost", "slippage_cost", "fees")), Decimal(0))
    right_cost = sum((Decimal(row[key]) for row in right_fills
                      for key in ("spread_cost", "slippage_cost", "fees")), Decimal(0))
    complete_pairs = [(Decimal(a["nav_brl"]), Decimal(b["nav_brl"]))
                      for a, b in zip(left_nav, right_nav) if a["nav_brl"] is not None]
    result["costs_nondecreasing"] = right_cost >= left_cost
    result["complete_nav_nonincreasing"] = all(b <= a for a, b in complete_pairs)
    result["nav_points_compared"] = len(complete_pairs)
    result["monotonicity"] = "PASS" if result["costs_nondecreasing"] and result["complete_nav_nonincreasing"] else "FAIL"
    if result["monotonicity"] == "FAIL" and raise_on_fail:
        raise ValueError("identical fills violate cost or NAV monotonicity")
    return result


def run_cost_sensitivity(snapshot, *, decision_ats, directory: str | Path) -> dict:
    """Persist nine separate runs, replay and audit each, then compare adjacent costs."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    runs = {}
    for strategy in STRATEGIES:
        runs[strategy] = {}
        for label, spread, slippage, fees in SCENARIOS:
            config = replace(F1Config(), half_spread_bps=Decimal(spread),
                             slippage_bps=Decimal(slippage), fees_bps=Decimal(fees))
            result = (run_f1_monthly(snapshot, decision_ats=decision_ats, config=config)
                      if strategy == "momentum" else
                      run_f2_control(snapshot, decision_ats=decision_ats, control_id=strategy,
                                     config=config))
            root = write_f1_run(snapshot, result, target / f"{strategy}-{label}")
            runs[strategy][label] = _report_run(root)
    comparisons = {strategy: {
        f"{a}_to_{b}": compare_pair(target / f"{strategy}-{a}", target / f"{strategy}-{b}")
        for a, b in (("zero", "base"), ("base", "high"))}
        for strategy in STRATEGIES}
    report = {"report_schema_version": 1, "synthetic": True,
              "scenarios_bps": {name: {"half_spread": a, "slippage": b, "fees": c}
                                for name, a, b, c in SCENARIOS},
              "runs": runs, "comparisons": comparisons}
    (target / "sensitivity.json").write_bytes(_json(report) + b"\n")
    return report
