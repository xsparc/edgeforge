"""Check one retained EdgeForge report against an explicit p95 latency budget."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from benchmark_receipt import REPORT_MAX_BYTES, read_bounded


class QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "budget: invalid arguments; use --help\n")


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate member")
        result[name] = value
    return result


def reject_constant(_: str) -> None:
    raise ValueError("nonfinite number")


def evaluate(report: Path, limit: Decimal) -> tuple[int, str]:
    data = json.loads(
        read_bounded(report, REPORT_MAX_BYTES).decode("utf-8"),
        parse_float=Decimal,
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
        raise ValueError("invalid report")
    if data["schema_version"] != 1:
        raise ValueError("unsupported report version")
    latencies = data.get("latency_ms")
    agreement = data.get("agreement")
    if not isinstance(latencies, dict) or not isinstance(agreement, dict):
        raise ValueError("missing evidence")
    p95 = latencies.get("p95")
    passed = agreement.get("passed")
    if (
        type(p95) not in (int, Decimal)
        or not Decimal(p95).is_finite()
        or p95 < 0
        or type(passed) is not bool
    ):
        raise ValueError("invalid evidence")
    if not passed:
        return 3, "agreement_failed"
    return (0, "within_budget") if p95 <= limit else (1, "above_budget")


def main(argv: list[str] | None = None) -> int:
    parser = QuietParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--max-p95-ms", required=True)
    args = parser.parse_args(argv)
    try:
        limit = Decimal(args.max_p95_ms)
        if not limit.is_finite() or limit <= 0:
            raise ValueError("invalid limit")
        code, outcome = evaluate(args.report, limit)
    except (OSError, ValueError, InvalidOperation, RecursionError):
        print("budget: invalid, unsupported, or unavailable report or limit", file=sys.stderr)
        return 2
    print(json.dumps({"schema_version": 1, "outcome": outcome}, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
