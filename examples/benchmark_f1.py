"""Time the three-cycle synthetic example and hash its economic outputs.

Run from any directory with the package available on PYTHONPATH.
Timings describe this local fixture, not market latency or profitability.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from qtre.backtest import run_f1_monthly
from qtre.data.snapshot import load_snapshot
from qtre.reporting import _json, replay_f1, write_f1_run


FIXTURE = Path(__file__).with_name("synthetic_f1_monthly_v1.json")
DECISIONS = tuple(datetime(2025, month, day, 20, 7, tzinfo=timezone.utc)
                  for month, day in ((1, 31), (2, 28), (3, 31)))


def measure(operation, repetitions):
    operation()  # Warm filesystem and parsing caches before timing.
    elapsed = []
    for _ in range(repetitions):
        start = perf_counter()
        result = operation()
        elapsed.append((perf_counter() - start) * 1000)
    return median(elapsed), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=11)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    snapshot = load_snapshot(FIXTURE)
    run_ms, result = measure(lambda: run_f1_monthly(snapshot, decision_ats=DECISIONS),
                             args.repetitions)
    with TemporaryDirectory() as tmp:
        directory = write_f1_run(snapshot, result, Path(tmp) / "run")
        replay_ms, _ = measure(lambda: replay_f1(directory), args.repetitions)
    # Exclude manifest/code identity so correct optimizations remain comparable.
    economic = {key: result[key] for key in ("orders", "order_states", "fills", "ledger", "nav")}
    print(json.dumps(dict(repetitions=args.repetitions, run_ms=run_ms,
                          replay_ms=replay_ms,
                          economic_hash=sha256(_json(economic)).hexdigest()), indent=2))


if __name__ == "__main__":
    main()
