---
name: quant-performance
description: Profile and safely optimize QTRE Python runtime or memory when a measured bottleneck warrants numerical benchmarking or vectorization.
---

# Quant Performance

Read `AGENTS.md`, the relevant contracts, and `examples/benchmark_f1.py`. Start with actual source, dependency, and hardware inspection. The current implementation is Python.

## Workflow

1. Define the workload, input identity, correctness invariant, target metric, and resource budget. Measure available RAM/swap and CPU before choosing concurrency; default to sequential local benchmarks on constrained hardware.
2. Capture code revision and working-tree status, Python/compiler versions, repetitions, warmup, dataset size, and machine load. Profile first; distinguish parsing, simulation, replay, allocation, and I/O. Do not equate a tiny synthetic workload with market execution latency.
3. Retain the existing scalar/reference behavior and economic-output hash before optimization. Check units, operation ordering, rounding, dtype, missing values, and deterministic tie-breaking; any altered financial semantics requires explicit authorization.
4. In Python, prefer eliminating repeated work and unnecessary copies before new dependencies. Vectorize only measured bottlenecks, account for temporary arrays and dtype/overflow, and use bounded chunks when memory dominates. Inspect `cProfile` and, when needed, `tracemalloc` rather than guessing.
5. Compare repeated timings with warmup and variation, alongside numerical regression/invariant tests. Avoid brittle wall-clock assertions in CI. Set tolerances from numerical error/financial precision, not from whatever makes a changed result pass. Record speed/memory tradeoffs and inconclusive measurements honestly.

## Expected outputs

- A reproducible baseline/profile and a proposed optimization tied to its measured hotspot.
- Before/after time and memory evidence with environment, sample size, correctness hash/tolerances, and test results.
- A recommendation that distinguishes observed gains, noise, and scaling assumptions.

## Practical validation example

From the repository root, use a small sequential benchmark:

```sh
PYTHONPATH=src python3 examples/benchmark_f1.py --repetitions 3
PYTHONPATH=src python3 -m cProfile -s cumulative examples/benchmark_f1.py --repetitions 1
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_f1_monthly.py' -v
```

Record the `economic_hash`, run/replay milliseconds, and profiler output. A repeat on unchanged inputs should preserve the economic hash; timing may vary. The benchmark covers the existing three-cycle fixture, while the monthly tests also cover a fourth cycle. Report those scopes explicitly and do not claim the profile proves large-universe scalability.
