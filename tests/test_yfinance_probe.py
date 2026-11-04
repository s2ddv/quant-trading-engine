from types import SimpleNamespace
import unittest

from qtre.data.yfinance_probe import probe


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
