"""Executable synthetic review acceptance; requires the installed ONNX extra."""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

from edgeforge.benchmark import benchmark
from edgeforge.bundle import pack, unpack
from edgeforge.cli import main as cli_main
from edgeforge.comparison import compare_reports, render_comparison_csv
from edgeforge.comparison_identity import comparison_identity
from edgeforge.comparison_review import read_source
from edgeforge.contracts import BenchmarkOptions


def require(condition):
    if not condition:
        raise RuntimeError("portable review acceptance failed")


def cli(arguments):
    with patch.object(sys, "argv", ["edgeforge", *map(str, arguments)]):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cli_main()


def run(directory: Path) -> dict:
    from edgeforge.example import example_assets

    directory.mkdir(parents=True, exist_ok=False)
    synthetic = {
        "schema_version": 1,
        "os": "test",
        "architecture": "synthetic",
        "python": "synthetic",
        "logical_cpus": 1,
        "system_ram_bytes": 1024,
        "packages": {
            key: None for key in ("numpy", "onnxruntime", "onnx", "executorch", "torch", "psutil")
        },
        "onnx_registered_providers": ["CPUExecutionProvider"],
        "accelerator_verification": "not-probed",
    }
    model, vectors, config = example_assets()
    with patch("edgeforge.benchmark.capabilities", return_value=synthetic):
        report = benchmark(
            unpack(pack(model, vectors, config)), BenchmarkOptions(warmup=1, iterations=2)
        )
    before = read_source(report.model_dump_json().encode())
    data = before.model_dump()
    data["runtime_version"] = "synthetic-after"
    data["agreement"].update(
        passed=False, elements_matching=0, fraction_matching=0.0, max_abs_error=1.0
    )
    after = type(before).model_validate(data)
    comparison = compare_reports(before, after)
    left, right, retained, identity = [
        directory / name
        for name in ("before.json", "after.json", "comparison.json", "identity.json")
    ]
    for path, value in [
        (left, before.model_dump()),
        (right, after.model_dump()),
        (retained, comparison.model_dump()),
        (identity, comparison_identity(comparison)),
    ]:
        with path.open("xb") as stream:
            stream.write((json.dumps(value, sort_keys=True) + "\n").encode())
    inputs = {p: p.read_bytes() for p in (left, right, retained, identity)}
    with patch(
        "edgeforge.benchmark.create_adapter", side_effect=RuntimeError("review invoked inference")
    ):
        for format in ("html", "csv"):
            output = directory / ("review." + format)
            args = [
                "comparison-review",
                retained,
                left,
                right,
                "--identity",
                identity,
                "--format",
                format,
                "--output",
                output,
            ]
            require(cli(args) == 0)
            saved = output.read_bytes()
            require(cli(args) == 2 and output.read_bytes() == saved)
        csv = directory / "review.csv"
        require(csv.read_bytes() == render_comparison_csv(comparison).encode())
        require(cli(["comparison-verify", left, right, csv, "--format", "csv"]) == 0)
        replacement = compare_reports(before, before)
        replaced = directory / "replaced.json"
        replaced_identity = directory / "replaced-identity.json"
        replaced.write_text(replacement.model_dump_json(), encoding="utf-8")
        replaced_identity.write_text(json.dumps(comparison_identity(replacement)), encoding="utf-8")
        require(cli(["comparison-check", replaced, "--identity", replaced_identity]) == 0)
        for format in ("html", "csv"):
            blocked = directory / ("blocked." + format)
            require(
                cli(
                    [
                        "comparison-review",
                        replaced,
                        left,
                        right,
                        "--identity",
                        replaced_identity,
                        "--format",
                        format,
                        "--output",
                        blocked,
                    ]
                )
                == 2
            )
            require(not blocked.exists())
        require(all(p.read_bytes() == raw for p, raw in inputs.items()))
    return {
        "verified": True,
        "formats": ["html", "csv"],
        "review_execution": "none",
        "fixture": "synthetic_failed_agreement",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.directory)))
    except Exception:
        print(json.dumps({"error": "acceptance_failed"}), file=sys.stderr)
        raise SystemExit(2) from None
