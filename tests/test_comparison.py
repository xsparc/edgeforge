import csv
import io
import json
import subprocess
import sys

import pytest
from test_reports import evidence as evidence

from edgeforge.benchmark import benchmark
from edgeforge.cli import main, parser, run
from edgeforge.comparison import ReportComparison, compare_reports, render_comparison_csv
from edgeforge.contracts import BenchmarkOptions
from edgeforge.reports import validate_report, verify_report_bundle


def test_native_source_bound_comparison_and_reverse(evidence, monkeypatch):
    _, bundle, raw = evidence
    before = validate_report(raw)
    after = validate_report(
        benchmark(bundle, BenchmarkOptions(iterations=2, warmup=1)).model_dump_json().encode()
    )
    verify_report_bundle(before, bundle)
    verify_report_bundle(after, bundle)
    changed = validate_report(
        benchmark(bundle, BenchmarkOptions(iterations=2, warmup=2)).model_dump_json().encode()
    )
    verify_report_bundle(changed, bundle)
    assert compare_reports(before, changed).incompatibility_reasons == ["options"]

    def forbidden(*args):
        pytest.fail("comparison must never execute a model")

    monkeypatch.setattr("edgeforge.benchmark.create_adapter", forbidden)
    result = compare_reports(before, after)
    reverse = compare_reports(after, before)
    assert result.compatible and not result.incompatibility_reasons
    assert result.interpretation == "descriptive_only_no_performance_verdict"
    assert result.hardware_identity == "not_established"
    assert result.before_report_sha256 == reverse.after_report_sha256
    for group in ("latency_ms_delta", "memory_delta", "storage_delta"):
        for name, value in getattr(result, group).model_dump().items():
            assert value == -getattr(getattr(reverse, group), name)
    assert ReportComparison.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("bundle_sha256", "a" * 64, "bundle"),
        ("runtime_version", "different", "runtime_version"),
        ("requested_provider", "another", "requested_provider"),
        ("active_providers", ["another"], "active_providers"),
        ("threads", 2, "threads"),
        ("edgeforge_version", "different", "edgeforge_version"),
    ],
)
def test_compatibility_reasons(evidence, field, value, reason):
    before = validate_report(evidence[2])
    data = before.model_dump()
    data[field] = value
    if value == getattr(before, field):
        data[field] = 3
    after = type(before).model_validate(data)
    result = compare_reports(before, after)
    assert not result.compatible and result.incompatibility_reasons == [reason]


def test_options_runtime_and_platform_reasons_are_ordered(evidence):
    before = validate_report(evidence[2])
    data = before.model_dump()
    data["options"]["warmup"] += 1
    data["runtime"] = "executorch"
    data["threads"] = None
    data["requested_provider"] = "portable"
    data["device"]["architecture"] = "other"
    result = compare_reports(before, type(before).model_validate(data))
    assert result.incompatibility_reasons == [
        "options",
        "runtime",
        "requested_provider",
        "threads",
        "device",
    ]


@pytest.mark.parametrize(
    "mutation", ["digest", "delta", "reason", "verdict", "version", "unknown", "nan", "source"]
)
def test_closed_contract_rejects_tampering(evidence, mutation):
    before = validate_report(evidence[2])
    data = compare_reports(before, before).model_dump()
    if mutation == "digest":
        data["before_report_sha256"] = "0" * 64
    elif mutation == "delta":
        data["memory_delta"]["rss_sampled_peak_bytes"] = 1
    elif mutation == "reason":
        data["incompatibility_reasons"] = ["device"]
    elif mutation == "verdict":
        data["compatible"] = False
    elif mutation == "version":
        data["schema_version"] = 1.0
    elif mutation == "unknown":
        data["speedup"] = 2
    elif mutation == "nan":
        data["latency_ms_delta"]["mean"] = float("nan")
    else:
        data["before"]["runtime_version"] = "altered"
    with pytest.raises(ValueError):
        ReportComparison.model_validate(data)


@pytest.mark.parametrize("format", ["json", "csv"])
def test_cli_exact_transport_exclusive_output_and_bounds(
    evidence, tmp_path, monkeypatch, capsys, format
):
    before = validate_report(evidence[2])
    data = before.model_dump()
    data["runtime_version"] = "=formula,\r\nÃ©â€ºÂª"
    after = type(before).model_validate(data)
    paths = [tmp_path / "before.json", tmp_path / "after.json"]
    for path, report in zip(paths, [before, after], strict=True):
        path.write_text(report.model_dump_json(), encoding="utf-8")
    originals = [p.read_bytes() for p in paths]
    comparison = compare_reports(before, after)
    expected = (
        render_comparison_csv(comparison)
        if format == "csv"
        else comparison.model_dump_json(indent=2) + "\n"
    ).encode()
    target = tmp_path / ("comparison." + format)
    args = ["report-compare", *map(str, paths), "--format", format]
    monkeypatch.setattr(sys, "argv", ["edgeforge", *args, "--output", str(target)])
    assert main() == 0 and target.read_bytes() == expected
    assert main() == 2 and target.read_bytes() == expected
    assert json.loads(capsys.readouterr().err) == {"error": "io_error"}
    result = subprocess.run(
        [sys.executable, "-m", "edgeforge.cli", *args], capture_output=True, check=True
    )
    assert result.stdout == expected
    assert [p.read_bytes() for p in paths] == originals
    if format == "csv":
        rows = list(csv.DictReader(io.StringIO(expected.decode(), newline="")))
        assert len(rows) == 10
        assert all(r["after_runtime_version_text"] == "text:=formula,\r\nÃ©â€ºÂª" for r in rows)
        assert all(r["incompatibility_reasons"] == "runtime_version" for r in rows)
    for path in paths:
        path.write_bytes(b" " * (256 * 1024 + 1))
        monkeypatch.setattr(sys, "argv", ["edgeforge", *args])
        assert main() == 2
        captured = capsys.readouterr()
        assert not captured.out and json.loads(captured.err) == {"error": "invalid_input"}
        path.write_bytes(originals[paths.index(path)])


def test_schema_export():
    schema = run(parser().parse_args(["comparison-schema"]))
    assert schema["additionalProperties"] is False
    assert schema["properties"]["direction"]["const"] == "after_minus_before"
    assert "before_report_sha256" in schema["required"]


def test_signed_numeric_csv_roundtrip_and_normalized_identity(evidence):
    before = validate_report(evidence[2])
    data = before.model_dump()
    for key in data["latency_ms"]:
        data["latency_ms"][key] += 1.0
    data["memory"]["rss_sampled_peak_bytes"] += 100
    data["memory"]["rss_sampled_increase_bytes"] += 100
    data["storage"]["bundle_bytes"] += 10
    after = type(before).model_validate(data)
    comparison = compare_reports(before, after)
    assert comparison.compatible  # Measurements are not configuration descriptors.
    rows = list(csv.DictReader(io.StringIO(render_comparison_csv(comparison), newline="")))
    for row in rows:
        number = float if row["group"] == "latency_ms" else int
        assert number(row["delta"]) == number(row["after"]) - number(row["before"])
    reverse = compare_reports(after, before)
    assert reverse.storage_delta.bundle_bytes == -10
    assert reverse.memory_delta.rss_sampled_peak_bytes == -100
    reformatted = validate_report(json.dumps(before.model_dump(), indent=4).encode())
    assert (
        compare_reports(reformatted, after).before_report_sha256 == comparison.before_report_sha256
    )
    data["latency_ms"]["mean"] = float("inf")
    with pytest.raises(ValueError):
        compare_reports(
            before,
            after.model_copy(
                update={"latency_ms": after.latency_ms.model_copy(update={"mean": float("inf")})}
            ),
        )
