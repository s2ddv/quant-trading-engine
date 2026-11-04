"""Exploratory Yahoo Finance coverage probe; never constructs a causal snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any


DEFAULT_TICKERS = ("PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA")
REQUIRED = ("Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits")


def probe(tickers: tuple[str, ...], start: str, end: str, *, yf_module: Any = None) -> dict[str, Any]:
    """Download daily raw OHLC and summarize coverage without storing prices."""
    if yf_module is None:
        import yfinance as yf_module
    if not tickers or len(set(tickers)) != len(tickers):
        raise ValueError("tickers must be nonempty and unique")
    from datetime import date
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError("end must be later than start")
    report = {
        "source": "Yahoo Finance via yfinance",
        "yfinance_version": getattr(yf_module, "__version__", "unknown"),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_inclusive": start,
        "end_exclusive": end,
        "interval": "1d",
        "auto_adjust": False,
        "actions": True,
        "repair": False,
        "purpose": "exploratory_data_quality_only",
        "causal_backtest_ready": False,
        "limitations": [
            "No historical available_at or revision history for each observation",
            "Input tickers are a selected cohort, not a historical listed universe",
            "Daily OHLC does not provide an independently timestamped opening event",
            "Data rights and corporate actions need source-level audit before publication",
        ],
        "instruments": [],
    }
    for ticker in tickers:
        item: dict[str, Any] = {"ticker": ticker}
        try:
            frame = yf_module.Ticker(ticker).history(
                start=start, end=end, interval="1d", auto_adjust=False,
                actions=True, repair=False, timeout=15,
            )
            missing_columns = sorted(set(REQUIRED) - set(frame.columns))
            item["missing_columns"] = missing_columns
            item["rows"] = len(frame)
            item["first_session"] = frame.index[0].date().isoformat() if len(frame) else None
            item["last_session"] = frame.index[-1].date().isoformat() if len(frame) else None
            item["duplicate_sessions"] = int(frame.index.normalize().duplicated().sum()) if len(frame) else 0
            if missing_columns or frame.empty:
                item["status"] = "INCOMPLETE"
            else:
                prices = frame[list(REQUIRED[:4])]
                item["missing_ohlc_rows"] = int(prices.isna().any(axis=1).sum())
                item["nonpositive_ohlc_rows"] = int((prices <= 0).any(axis=1).sum())
                item["zero_volume_rows"] = int((frame["Volume"] == 0).sum())
                item["dividend_events"] = int((frame["Dividends"].fillna(0) != 0).sum())
                item["split_events"] = int((frame["Stock Splits"].fillna(0) != 0).sum())
                item["status"] = "OBSERVED" if not (item["missing_ohlc_rows"] or item["nonpositive_ohlc_rows"] or item["duplicate_sessions"]) else "INCOMPLETE"
        except Exception as exc:
            item["status"] = "FETCH_ERROR"
            item["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        report["instruments"].append(item)
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Audit exploratory yfinance coverage; no backtest")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2025-03-01")
    parser.add_argument("tickers", nargs="*", default=list(DEFAULT_TICKERS))
    args = parser.parse_args()
    print(json.dumps(probe(tuple(args.tickers), args.start, args.end), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
