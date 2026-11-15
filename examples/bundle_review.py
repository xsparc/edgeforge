"""Portable bundle review with entirely synthetic evidence and no inference."""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

from edgeforge.cli import main
from edgeforge.reports import ReportEvidence


def synthetic():
    return ReportEvidence.model_validate(
        {
            "schema_version": 1,
            "edgeforge_version": "synthetic",
            "bundle_sha256": "a" * 64,
            "measured_at": "2026-01-01T00:00:00+00:00",
            "runtime": "onnx",
            "runtime_version": "synthetic",
            "requested_provider": "CPUExecutionProvider",
            "active_providers": ["CPUExecutionProvider"],
            "threads": 1,
            "options": {"warmup": 0, "iterations": 1, "atol": 0.0, "rtol": 0.0},
            "cases": 1,
            "latency_ms": {k: 1.0 for k in ("min", "mean", "p50", "p95", "max")},
            "memory": {
                "rss_before_load_bytes": 1,
                "rss_sampled_peak_bytes": 2,
                "rss_sampled_increase_bytes": 1,
                "scope": "whole-process RSS sampled after load and inference; not device VRAM",
            },
            "storage": {"model_bytes": 1, "bundle_bytes": 2},
            "agreement": {
                "passed": False,
                "finite": True,
                "elements_compared": 1,
                "elements_matching": 0,
                "fraction_matching": 0.0,
                "max_abs_error": 1.0,
                "scope": "golden-output numerical agreement; not task-level accuracy",
            },
            "device": {
                "schema_version": 1,
                "os": "test",
                "architecture": "synthetic",
                "python": "synthetic",
                "logical_cpus": 1,
                "system_ram_bytes": 1,
                "packages": {
                    k: None
                    for k in ("numpy", "onnxruntime", "onnx", "executorch", "torch", "psutil")
                },
                "onnx_registered_providers": [],
                "accelerator_verification": "not-probed",
            },
            "measurement_scope": "serial adapter call including tensor conversion "
            "and materialization; "
            "excludes model load, preprocessing, RSS sampling and comparison",
        }
    )


def require(value):
    if not value:
        raise RuntimeError("bundle review acceptance failed")


def cli(args):
    with patch.object(sys, "argv", ["edgeforge", *map(str, args)]):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main()


def run(directory: Path):
    directory.mkdir(parents=True, exist_ok=False)
    left, right, bundle, identity = [
        directory / n for n in ("before.json", "after.json", "bundle.json", "identity.json")
    ]
    a = synthetic()
    data = a.model_dump()
    data["runtime_version"] = "changed"
    b = ReportEvidence.model_validate(data)
    for path, source in [(left, a), (right, b)]:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(source.model_dump_json())
    with patch("edgeforge.benchmark.create_adapter", side_effect=RuntimeError("inference invoked")):
        require(cli(["comparison-bundle", left, right, "--output", bundle]) == 0)
        require(cli(["comparison-bundle-identity", bundle, "--output", identity]) == 0)
        saved = {p: p.read_bytes() for p in (left, right, bundle, identity)}
        require(cli(["comparison-bundle-identity", bundle, "--output", identity]) == 2)
        require(cli(["comparison-bundle-verify", bundle, "--identity", identity]) == 0)
        replaced = directory / "replaced.json"
        replaced_id = directory / "replaced-identity.json"
        require(cli(["comparison-bundle", left, left, "--output", replaced]) == 0)
        require(cli(["comparison-bundle-identity", replaced, "--output", replaced_id]) == 0)
        require(cli(["comparison-bundle-verify", replaced, "--identity", replaced_id]) == 0)
        require(cli(["comparison-bundle-verify", replaced, "--identity", identity]) == 2)
        for format in ("html", "csv"):
            output = directory / ("review." + format)
            source_args = ["--before", left, "--after", right]
            render = [
                "comparison-bundle-render",
                bundle,
                "--format",
                format,
                "--output",
                output,
                "--identity",
                identity,
                *source_args,
            ]
            require(cli(render) == 0)
            saved[output] = output.read_bytes()
            require(cli(render) == 2)
            verify = [
                "comparison-bundle-verify-export",
                bundle,
                output,
                "--format",
                format,
                "--identity",
                identity,
                *source_args,
            ]
            require(cli(verify) == 0)
            edited = directory / ("edited." + format)
            edited.write_bytes(saved[output] + b"\n")
            require(
                cli(
                    [
                        "comparison-bundle-verify-export",
                        bundle,
                        edited,
                        "--format",
                        format,
                        "--identity",
                        identity,
                    ]
                )
                == 2
            )
            blocked = directory / ("blocked." + format)
            require(
                cli(
                    [
                        "comparison-bundle-render",
                        replaced,
                        "--identity",
                        replaced_id,
                        "--output",
                        blocked,
                        *source_args,
                    ]
                )
                == 2
            )
            require(not blocked.exists())
        require(all(p.read_bytes() == raw for p, raw in saved.items()))
    return {"verified": True, "formats": ["html", "csv"], "inference": "none"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.directory)))
    except Exception:
        print(json.dumps({"error": "acceptance_failed"}), file=sys.stderr)
        raise SystemExit(2) from None
