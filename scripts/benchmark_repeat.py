"""Summarize p95 stability across comparable retained EdgeForge reports."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

from benchmark_budget import reject_constant, unique_object
from benchmark_receipt import REPORT_MAX_BYTES, read_bounded

MAX_RUNS = 16
LABEL_FIELDS = (
    "edgeforge_version",
    "runtime",
    "runtime_version",
    "requested_provider",
    "measurement_scope",
)


class QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "repeat: invalid arguments; use --help\n")


def load_run(path: Path) -> tuple[tuple, datetime, float, bool]:
    data = json.loads(
        read_bounded(path, REPORT_MAX_BYTES).decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError
    if data["schema_version"] != 1:
        raise ValueError

    labels = tuple(data.get(name) for name in LABEL_FIELDS)
    if not all(isinstance(label, str) and label.strip() for label in labels):
        raise ValueError
    digest = data.get("bundle_sha256")
    if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
        raise ValueError
    providers = data.get("active_providers")
    if not isinstance(providers, list) or not all(
        isinstance(provider, str) and provider.strip() for provider in providers
    ):
        raise ValueError
    cases, threads = data.get("cases"), data["threads"]
    if type(cases) is not int or cases < 1:
        raise ValueError
    if threads is not None and (type(threads) is not int or threads < 1):
        raise ValueError
    options, device = data.get("options"), data.get("device")
    if not isinstance(options, dict) or set(options) != {"warmup", "iterations", "atol", "rtol"}:
        raise ValueError
    for name, low, high in (("warmup", 0, 100), ("iterations", 1, 10_000)):
        if type(options[name]) is not int or not low <= options[name] <= high:
            raise ValueError
    for name in ("atol", "rtol"):
        if type(options[name]) not in (int, float) or not 0 <= options[name] <= 1:
            raise ValueError
    if not isinstance(device, dict) or not device:
        raise ValueError
    descriptors = json.dumps([options, device], sort_keys=True, allow_nan=False)
    signature = (labels, digest, tuple(providers), cases, threads, descriptors)

    timestamp = datetime.fromisoformat(data["measured_at"])
    if timestamp.utcoffset() is None:
        raise ValueError
    p95 = data["latency_ms"]["p95"]
    passed = data["agreement"]["passed"]
    if type(p95) not in (int, float) or not math.isfinite(p95) or p95 < 0:
        raise ValueError
    if type(passed) is not bool:
        raise ValueError
    return signature, timestamp, float(p95), passed


def summarize(paths: list[Path]) -> tuple[int, dict]:
    if not 2 <= len(paths) <= MAX_RUNS:
        raise ValueError
    runs = [load_run(path) for path in paths]
    if len({run[1] for run in runs}) != len(runs):
        raise ValueError
    result = {"schema_version": 1, "report_count": len(runs)}
    if any(not run[3] for run in runs):
        return 3, {**result, "outcome": "agreement_failed"}
    if any(run[0] != runs[0][0] for run in runs[1:]):
        return 1, {**result, "outcome": "incomparable"}
    values = sorted(run[2] for run in runs)
    lower = values[(len(values) - 1) // 2]
    upper = values[len(values) // 2]
    return 0, {
        **result,
        "outcome": "summarized",
        "report_p95_ms": {
            "min": values[0],
            "median": lower + (upper - lower) / 2,
            "max": values[-1],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = QuietParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("reports", type=Path, metavar="REPORT", nargs="+")
    args = parser.parse_args(argv)
    try:
        code, result = summarize(args.reports)
    except (KeyError, OSError, OverflowError, RecursionError, TypeError, ValueError):
        print("repeat: invalid, unsupported, or unavailable report set", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
