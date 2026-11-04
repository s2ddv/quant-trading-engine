from types import SimpleNamespace
from datetime import datetime, timezone
from io import StringIO
import unittest
from unittest.mock import patch

from qtre.data.yfinance_probe import REQUIRED, main, probe, summarize_history


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, **kwargs):
        self.kwargs = kwargs
        raise ConnectionError("offline")


class YfinanceProbeTests(unittest.TestCase):
    def test_network_failure_is_reported_without_causal_claim(self):
        fake = SimpleNamespace(__version__="test", Ticker=FakeTicker)
        report = probe(("SYN.SA",), "2024-01-01", "2025-01-01", yf_module=fake)
        self.assertFalse(report["causal_backtest_ready"])
        self.assertEqual(report["instruments"][0]["status"], "FETCH_ERROR")
        self.assertIn("ConnectionError", report["instruments"][0]["error"])

    def test_rejects_invalid_period_and_duplicate_symbols(self):
        fake = SimpleNamespace(Ticker=FakeTicker)
        with self.assertRaises(ValueError):
            probe(("A", "A"), "2024-01-01", "2025-01-01", yf_module=fake)
        with self.assertRaises(ValueError):
            probe(("A",), "2025-01-01", "2024-01-01", yf_module=fake)


class FakeFrame:
    """Minimal provider boundary; these tests need neither pandas nor network."""
    columns = REQUIRED

    def __init__(self):
        self.rows = [(datetime(2024, 1, 2, tzinfo=timezone.utc), dict(
            Open=10, High=12, Low=9, Close=11, Volume=1000,
            Dividends=1, **{"Stock Splits": 0}))]

    def iterrows(self):
        return iter(self.rows)


class YfinanceQualityTests(unittest.TestCase):
    def summarize(self, frame):
        return summarize_history(frame, "2024-01-01", "2025-01-01")

    def test_provider_success_preserves_missing_rows_and_request_settings(self):
        calls = []

        def history(**kwargs):
            calls.append(kwargs)
            return FakeFrame()

        fake = SimpleNamespace(__version__="test", Ticker=lambda _: SimpleNamespace(history=history))
        report = probe(("SYN.SA",), "2024-01-01", "2025-01-01", yf_module=fake)
        self.assertTrue(calls[0]["keepna"])
        self.assertFalse(calls[0]["auto_adjust"])
        self.assertFalse(calls[0]["repair"])
        self.assertTrue(calls[0]["actions"])
        self.assertEqual(report["instruments"][0]["status"], "OBSERVED")
        self.assertEqual(report["instruments"][0]["dividend_events"], 1)

    def test_invalid_prices_volume_and_actions_are_never_certified(self):
        for key, value, counter in (("High", 8, "inconsistent_ohlc_rows"),
                                    ("Close", float("inf"), "nonfinite_ohlc_rows"),
                                    ("Close", float("nan"), "missing_ohlc_rows"),
                                    ("Close", 0, "nonpositive_ohlc_rows"),
                                    ("Volume", -1, "invalid_volume_rows"),
                                    ("Volume", 1.5, "invalid_volume_rows"),
                                    ("Dividends", None, "invalid_action_rows"),
                                    ("Stock Splits", -2, "invalid_action_rows")):
            frame = FakeFrame()
            frame.rows[0][1][key] = value
            with self.subTest(key=key, value=value):
                item = self.summarize(frame)
                self.assertEqual(item["status"], "INCOMPLETE")
                self.assertEqual(item[counter], 1)

    def test_empty_missing_columns_dates_and_duplicates(self):
        self.assertEqual(self.summarize(None)["status"], "INCOMPLETE")
        frame = FakeFrame()
        frame.columns = ("Close",)
        self.assertEqual(self.summarize(frame)["status"], "INCOMPLETE")
        frame = FakeFrame()
        frame.rows *= 2
        self.assertEqual(self.summarize(frame)["duplicate_sessions"], 1)
        frame.rows[0] = (datetime(2025, 1, 1), frame.rows[0][1])
        item = self.summarize(frame)
        self.assertEqual(item["out_of_range_rows"], 1)  # end is exclusive
        self.assertEqual(item["naive_timestamp_rows"], 1)
        self.assertTrue(item["unordered_sessions"])

    def test_zero_volume_requires_review(self):
        frame = FakeFrame()
        frame.rows[0][1]["Volume"] = 0
        self.assertEqual(self.summarize(frame)["status"], "REVIEW")

    def test_cli_fails_when_collection_is_incomplete(self):
        with patch("sys.argv", ["probe"]), patch("sys.stdout", new_callable=StringIO):
            for status, code in (("FETCH_ERROR", 2), ("INCOMPLETE", 2), ("REVIEW", 0), ("OBSERVED", 0)):
                with patch("qtre.data.yfinance_probe.probe", return_value={"instruments": [{"status": status}]}):
                    self.assertEqual(main(), code)
