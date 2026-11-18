import json
import sys
from pathlib import Path

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main
from edgeforge.comparison_bundle import (
    MAX_COMPARISON_BUNDLE_BYTES,
    ComparisonBundle,
    create_bundle,
    encode_bundle,
    read_bundle,
)
from edgeforge.comparison_review import read_source
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


def test_contract_schema_bounds_and_tampering(monkeypatch):
    a = synthetic()
    data = a.model_dump()
    data["runtime_version"] = "changed"
    b = ReportEvidence.model_validate(data)
    bundle = create_bundle(a, b)
    raw = encode_bundle(bundle)
    assert read_bundle(raw) == bundle
    assert not read_bundle(raw).before.agreement.passed
    assert encode_bundle(read_bundle(json.dumps(bundle.model_dump(), indent=2).encode())) == raw
    assert (
        json.loads(Path("schemas/comparison-bundle.schema.json").read_text())
        == ComparisonBundle.model_json_schema()
    )
    assert ComparisonBundle.model_json_schema()["additionalProperties"] is False
    for field, value in [
        ("schema_version", True),
        ("schema_version", 2),
        ("schema_version", 1.0),
        ("extra", 1),
        ("interpretation", "trusted"),
    ]:
        bad = bundle.model_dump()
        bad[field] = value
        with pytest.raises(ValueError):
            read_bundle(json.dumps(bad).encode())
    for field in ("before", "after", "comparison"):
        bad = bundle.model_dump()
        del bad[field]
        with pytest.raises(ValueError):
            read_bundle(json.dumps(bad).encode())
    bad = bundle.model_dump()
    bad["after"] = a.model_dump()
    with pytest.raises(ValueError):
        read_bundle(json.dumps(bad).encode())
    from edgeforge.errors import EdgeForgeError

    for bad in [
        b"{",
        b"\xff",
        b"[" * 2000,
        b"x" * (MAX_COMPARISON_BUNDLE_BYTES + 1),
        raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1),
        raw.replace(b'"mean":1.0', b'"mean":NaN', 1),
    ]:
        with pytest.raises((ValueError, EdgeForgeError)):
            read_bundle(bad)
    monkeypatch.setattr("edgeforge.comparison_review.MAX_REPORT_BYTES", 10)
    with pytest.raises(EdgeForgeError):
        create_bundle(a, b)


def check_cli(a, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("inference")
    )
    before, after, output = [tmp_path / n for n in ("before.json", "after.json", "bundle.json")]
    before.write_text(a.model_dump_json())
    data = a.model_dump()
    data["runtime_version"] = "changed"
    after.write_text(ReportEvidence.model_validate(data).model_dump_json())
    saved = {p: p.read_bytes() for p in (before, after)}

    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    assert cli(["comparison-bundle", before, after, "--output", output]) == 0
    raw = output.read_bytes()
    assert cli(["comparison-bundle-verify", output]) == 0
    assert cli(["comparison-bundle", before, after, "--output", output]) == 2
    assert output.read_bytes() == raw
    assert cli(["comparison-bundle-schema"]) == 0
    assert all(p.read_bytes() == content for p, content in saved.items())
    output.write_bytes(raw.replace(b'"schema_version":1', b'"schema_version":2', 1))
    assert cli(["comparison-bundle-verify", output]) == 2
    after.write_bytes(b"{}")
    blocked = tmp_path / "blocked"
    assert cli(["comparison-bundle", before, after, "--output", blocked]) == 2
    assert not blocked.exists()
    assert str(tmp_path) not in capsys.readouterr().err


def test_synthetic_cli(tmp_path, monkeypatch, capsys):
    check_cli(synthetic(), tmp_path, monkeypatch, capsys)


def test_native_cli(evidence, tmp_path, monkeypatch, capsys):
    check_cli(read_source(evidence[2]), tmp_path, monkeypatch, capsys)
