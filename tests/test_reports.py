import csv
import io
import json
import subprocess
import sys

import pytest

from edgeforge.benchmark import benchmark
from edgeforge.bundle import pack, unpack
from edgeforge.cli import main, parser, run
from edgeforge.contracts import BenchmarkOptions
from edgeforge.errors import EdgeForgeError
from edgeforge.reports import (
    MAX_REPORT_BYTES,
    ReportEvidence,
    render_report_csv,
    validate_report,
    verify_report_bundle,
)


@pytest.fixture
def evidence(monkeypatch):
    pytest.importorskip("onnxruntime")
    from edgeforge.example import example_assets

    monkeypatch.setattr(
        "edgeforge.benchmark.capabilities",
        lambda: {
            "schema_version": 1,
            "os": "test",
            "architecture": "synthetic",
            "python": "3.12",
            "logical_cpus": 1,
            "system_ram_bytes": 1024,
            "packages": {
                key: None
                for key in ("numpy", "onnxruntime", "onnx", "executorch", "torch", "psutil")
            },
            "onnx_registered_providers": ["CPUExecutionProvider"],
            "accelerator_verification": "not-probed",
        },
    )
    model, vectors, config = example_assets()
    bundle_bytes = pack(model, vectors, config)
    bundle = unpack(bundle_bytes)
    original = benchmark(bundle, BenchmarkOptions(iterations=2, warmup=1))
    return bundle_bytes, bundle, original.model_dump_json().encode()


def test_native_workflow_schema_and_read_only_source_check(evidence, tmp_path, monkeypatch, capsys):
    bundle_bytes, bundle, raw = evidence
    report = validate_report(raw)
    assert report.agreement.passed
    assert report.model_dump() == json.loads(raw)
    verify_report_bundle(report, bundle)
    schema = run(parser().parse_args(["report-schema"]))
    assert schema["properties"]["schema_version"]["const"] == 1
    assert schema["$defs"]["Latency"]["additionalProperties"] is False
    path, source = tmp_path / "report.json", tmp_path / "source.efb"
    path.write_bytes(raw)
    source.write_bytes(bundle_bytes)

    def forbidden(*args):
        pytest.fail("offline review must not execute a model")

    monkeypatch.setattr("edgeforge.benchmark.create_adapter", forbidden)
    result = run(parser().parse_args(["report-check", str(path), "--bundle", str(source)]))
    assert result["valid"] and result["bundle_checked"]
    assert path.read_bytes() == raw and source.read_bytes() == bundle_bytes
    target = tmp_path / "review.csv"
    args = ["edgeforge", "report-csv", str(path), "--output", str(target)]
    monkeypatch.setattr(sys, "argv", args)
    assert main() == 0
    assert main() == 2
    assert json.loads(capsys.readouterr().err) == {"error": "io_error"}
    stdout = subprocess.run(
        [sys.executable, "-m", "edgeforge.cli", "report-csv", str(path)],
        capture_output=True,
        check=True,
    ).stdout
    assert stdout == target.read_bytes() == render_report_csv(report).encode("utf-8")


@pytest.mark.parametrize(
    "mutation",
    [
        "version",
        "digest",
        "latency",
        "memory",
        "fraction",
        "verdict",
        "negative",
        "extra",
        "device",
        "time",
        "nonfinite",
    ],
)
def test_invalid_report_evidence_rejected(evidence, mutation):
    data = json.loads(evidence[2])
    if mutation == "version":
        data["schema_version"] = True
    elif mutation == "digest":
        data["bundle_sha256"] = "invalid"
    elif mutation == "latency":
        data["latency_ms"]["min"] = data["latency_ms"]["max"] + 1
    elif mutation == "memory":
        data["memory"]["rss_sampled_increase_bytes"] += 1
    elif mutation == "fraction":
        data["agreement"]["fraction_matching"] = 0.25
    elif mutation == "verdict":
        data["agreement"]["passed"] = False
    elif mutation == "negative":
        data["cases"] = -1
    elif mutation == "extra":
        data["latency_ms"]["unrecognized"] = 1.0
    elif mutation == "device":
        data["device"]["hostname"] = "private_marker"
    elif mutation == "time":
        data["measured_at"] = "2026-10-29T12:00:00"
    else:
        data["latency_ms"]["mean"] = float("inf")
    with pytest.raises(ValueError):
        validate_report(json.dumps(data).encode())


@pytest.mark.parametrize(
    "field,value",
    [
        ("bundle_sha256", "a" * 64),
        ("threads", 2),
        ("requested_provider", "different"),
        ("cases", 1),
    ],
)
def test_source_check_rejects_self_consistent_wrong_identity(evidence, field, value):
    _, bundle, raw = evidence
    data = json.loads(raw)
    data[field] = value
    with pytest.raises(EdgeForgeError):
        verify_report_bundle(validate_report(json.dumps(data).encode()), bundle)


def test_csv_prefixes_labels_and_round_trips_numbers(evidence):
    data = json.loads(evidence[2])
    data["runtime_version"] = '=formula,"雪"\r\n'
    data["requested_provider"] = "+provider"
    data["active_providers"] = ["@provider"]
    report = ReportEvidence.model_validate(data)
    rows = list(csv.DictReader(io.StringIO(render_report_csv(report), newline="")))
    assert len(rows) == 1
    row = rows[0]
    assert row["runtime_version_text"] == "text:" + data["runtime_version"]
    assert row["requested_provider_text"] == "text:+provider"
    assert row["active_providers_text"] == "text:@provider"
    assert int(row["elements_compared"]) == report.agreement.elements_compared
    assert float(row["p95_ms"]) == report.latency_ms.p95


def test_invalid_and_oversized_input_never_creates_output(evidence, tmp_path, monkeypatch, capsys):
    path, target = tmp_path / "private_marker.json", tmp_path / "review.csv"
    for raw in (b"private_marker", evidence[2] + b" " * MAX_REPORT_BYTES):
        path.write_bytes(raw)
        monkeypatch.setattr(
            sys, "argv", ["edgeforge", "report-csv", str(path), "--output", str(target)]
        )
        assert main() == 2
        assert not target.exists() and path.read_bytes() == raw
        result = capsys.readouterr()
        assert result.out == "" and json.loads(result.err) == {"error": "invalid_input"}


def test_failed_agreement_is_valid_evidence(evidence):
    data = json.loads(evidence[2])
    data["agreement"].update(passed=False, elements_matching=0, fraction_matching=0.0)
    report = validate_report(json.dumps(data).encode())
    assert not report.agreement.passed
    verify_report_bundle(report, evidence[1])
