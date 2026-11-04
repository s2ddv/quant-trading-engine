"""Exploratory Yahoo Finance coverage probe; never constructs a causal snapshot."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import math
from typing import Any


DEFAULT_TICKERS = ("PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA")
REQUIRED = ("Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits")


def _number(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def summarize_history(frame, start: str, end: str) -> dict[str, Any]:
    """Inspect all supplied records, without dropping, filling or sorting them."""
    columns = list(frame.columns) if frame is not None else []
    item: dict[str, Any] = dict(
        missing_columns=sorted(set(REQUIRED) - set(columns)),
        duplicate_columns=len(columns) != len(set(columns)), rows=0,
        first_session=None, last_session=None, duplicate_sessions=0,
        unordered_sessions=False, invalid_session_rows=0, naive_timestamp_rows=0,
        out_of_range_rows=0, missing_ohlc_rows=0, nonfinite_ohlc_rows=0,
        nonpositive_ohlc_rows=0, inconsistent_ohlc_rows=0, invalid_volume_rows=0,
        invalid_action_rows=0, zero_volume_rows=0, dividend_events=0, split_events=0,
    )
    days = []
    if frame is not None:
        for timestamp, row in frame.iterrows():
            item["rows"] += 1
            if not isinstance(timestamp, datetime) or timestamp != timestamp:
                item["invalid_session_rows"] += 1
            else:
                day = timestamp.date().isoformat()
                days.append(day)
                item["naive_timestamp_rows"] += int(timestamp.tzinfo is None or timestamp.utcoffset() is None)
                item["out_of_range_rows"] += int(not start <= day < end)
            if item["missing_columns"] or item["duplicate_columns"]:
                continue
            raw_prices = [row[name] for name in REQUIRED[:4]]
            prices = [_number(value) for value in raw_prices]
            item["missing_ohlc_rows"] += int(any(_missing(value) for value in raw_prices))
            item["nonfinite_ohlc_rows"] += int(any(value is None for value in prices))
            item["nonpositive_ohlc_rows"] += int(any(value is not None and value <= 0 for value in prices))
            if all(value is not None for value in prices):
                opening, high, low, close = prices
                item["inconsistent_ohlc_rows"] += int(high < max(opening, low, close) or low > min(opening, high, close))
            volume = _number(row["Volume"])
            item["invalid_volume_rows"] += int(volume is None or volume < 0 or not volume.is_integer())
            item["zero_volume_rows"] += int(volume == 0)
            dividend, split = _number(row["Dividends"]), _number(row["Stock Splits"])
            item["invalid_action_rows"] += int(dividend is None or split is None or dividend < 0 or split < 0)
            item["dividend_events"] += int(dividend is not None and dividend > 0)
            item["split_events"] += int(split is not None and split > 0)
    item["first_session"] = min(days) if days else None
    item["last_session"] = max(days) if days else None
    item["duplicate_sessions"] = len(days) - len(set(days))
    item["unordered_sessions"] = days != sorted(days)
    errors = ("missing_columns", "duplicate_columns", "duplicate_sessions", "unordered_sessions",
              "invalid_session_rows", "naive_timestamp_rows", "out_of_range_rows", "nonfinite_ohlc_rows",
              "nonpositive_ohlc_rows", "inconsistent_ohlc_rows", "invalid_volume_rows", "invalid_action_rows")
    item["status"] = "INCOMPLETE" if not item["rows"] or any(item[key] for key in errors) else "OBSERVED"
    if item["status"] == "OBSERVED" and item["zero_volume_rows"]:
        item["status"] = "REVIEW"
    return item


def probe(tickers: tuple[str, ...], start: str, end: str, *, yf_module: Any = None) -> dict[str, Any]:
    """Fetch daily provider OHLC; auto_adjust=False does not certify raw prices."""
    if not tickers or any(not isinstance(t, str) or not t.strip() or t != t.strip() for t in tickers):
        raise ValueError("tickers must be nonempty strings")
    if len({t.upper() for t in tickers}) != len(tickers):
        raise ValueError("tickers must be unique")
    if date.fromisoformat(start).isoformat() != start or date.fromisoformat(end).isoformat() != end:
        raise ValueError("dates must be canonical YYYY-MM-DD")
    if start >= end:
        raise ValueError("end must be later than start")
    if yf_module is None:
        import yfinance as yf_module
    report = {
        "source": "Yahoo Finance via yfinance",
        "yfinance_version": getattr(yf_module, "__version__", "unknown"),
        "retrieval_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_inclusive": start, "end_exclusive": end, "interval": "1d",
        "auto_adjust": False, "actions": True, "repair": False, "keepna": True,
        "purpose": "exploratory_data_quality_only", "causal_backtest_ready": False,
        "limitations": [
            "No historical available_at or revision history for each observation",
            "Input tickers are a selected cohort, not a historical listed universe",
            "Daily OHLC does not provide an independently timestamped opening event",
            "auto_adjust=False disables extra adjustment; it does not certify original traded prices",
            "No official calendar comparison: absent rows cannot be distinguished from closed sessions",
            "Data rights and corporate actions need source-level audit before publication",
        ],
        "instruments": [],
    }
    for ticker in tickers:
        item: dict[str, Any] = {"ticker": ticker}
        try:
            frame = yf_module.Ticker(ticker).history(
                start=start, end=end, interval="1d", auto_adjust=False,
                actions=True, repair=False, keepna=True, timeout=15,
            )
        except Exception as exc:
            item.update(status="FETCH_ERROR", error=f"{type(exc).__name__}: {str(exc)[:200]}")
        else:
            try:
                item.update(summarize_history(frame, start, end))
            except (TypeError, ValueError, AttributeError, KeyError) as exc:
                item.update(status="INVALID_RESPONSE", error=f"{type(exc).__name__}: {str(exc)[:200]}")
        item["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["instruments"].append(item)
    report["retrieval_finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Audit exploratory yfinance coverage; no backtest")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2025-03-01")
    parser.add_argument("tickers", nargs="*", default=list(DEFAULT_TICKERS))
    args = parser.parse_args()
    report = probe(tuple(args.tickers), args.start, args.end)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if any(item["status"] not in ("OBSERVED", "REVIEW") for item in report["instruments"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
