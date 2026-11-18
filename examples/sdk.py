"""Run after generating demo/example.efb with the CLI."""

from pathlib import Path

from edgeforge.benchmark import benchmark
from edgeforge.bundle import MAX_BUNDLE_BYTES, read_bounded, unpack
from edgeforge.contracts import BenchmarkOptions

bundle = unpack(read_bounded(Path("demo/example.efb"), MAX_BUNDLE_BYTES))
report = benchmark(bundle, BenchmarkOptions(warmup=5, iterations=50))
print(report.model_dump_json(indent=2))
raise SystemExit(0 if report.agreement["passed"] else 3)
