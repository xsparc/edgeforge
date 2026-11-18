import csv
import io
import json
import sys

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main
from edgeforge.comparison import MAX_COMPARISON_BYTES, compare_reports, render_comparison_csv
from edgeforge.comparison_review import (
    read_comparison,
    read_source,
    render_comparison_html,
    verify_comparison,
)
from edgeforge.errors import EdgeForgeError


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "nested_duplicate",
        "version",
        "extra",
        "delta",
        "digest",
        "invalid_utf8",
        "oversize",
        "deep",
        "nan",
    ],
)
def test_retained_intake_rejects_invalid_evidence(evidence, mutation):
    source = read_source(evidence[2])
    comparison = compare_reports(source, source)
    raw = comparison.model_dump_json().encode()
    assert read_comparison(raw) == comparison
    data = json.loads(raw)
    if mutation == "missing":
        del data["schema_version"]
    elif mutation == "version":
        data["schema_version"] = 1.0
    elif mutation == "extra":
        data["private_marker"] = 1
    elif mutation == "delta":
        data["storage_delta"]["model_bytes"] = 1
    elif mutation == "digest":
        data["before_report_sha256"] = "0" * 64
    elif mutation == "nan":
        data["latency_ms_delta"]["mean"] = float("nan")
    raw = json.dumps(data).encode()
    if mutation == "duplicate":
        raw = b'{"schema_version":1,' + raw[1:]
    elif mutation == "nested_duplicate":
        raw = raw.replace(b'"warmup":', b'"warmup":0,"warmup":', 1)
    elif mutation == "invalid_utf8":
        raw = b"\xff"
    elif mutation == "oversize":
        raw = b" " * (MAX_COMPARISON_BYTES + 1)
    elif mutation == "deep":
        raw = b"[" * 2000 + b"0" + b"]" * 2000
    with pytest.raises((ValueError, EdgeForgeError)):
        read_comparison(raw)


@pytest.mark.parametrize("format", ["json", "csv"])
def test_source_verification_rejects_consistent_replacements_and_reverse(evidence, format):
    before = read_source(evidence[2])
    data = before.model_dump()
    data["runtime_version"] = "different"
    after = type(before).model_validate(data)
    comparison = compare_reports(before, after)
    raw = (
        comparison.model_dump_json() if format == "json" else render_comparison_csv(comparison)
    ).encode()
    assert verify_comparison(before, after, raw, format=format) == comparison
    with pytest.raises(EdgeForgeError):
        verify_comparison(after, before, raw, format=format)
    with pytest.raises(EdgeForgeError):
        verify_comparison(before, before, raw, format=format)
    if format == "json":
        assert (
            verify_comparison(before, after, json.dumps(comparison.model_dump(), indent=4).encode())
            == comparison
        )


@pytest.mark.parametrize(
    "mutation", ["header", "cell", "order", "extra", "missing", "lf", "prefix", "utf8", "oversize"]
)
def test_csv_exact_contract(evidence, mutation):
    source = read_source(evidence[2])
    raw = render_comparison_csv(compare_reports(source, source)).encode()
    rows = list(csv.reader(io.StringIO(raw.decode(), newline="")))
    if mutation == "header":
        rows[0][0] = "unknown"
    elif mutation == "cell":
        rows[1][12] = "999"
    elif mutation == "order":
        rows[1:] = reversed(rows[1:])
    elif mutation == "extra":
        rows.append(rows[-1])
    elif mutation == "missing":
        rows.pop()
    elif mutation == "prefix":
        rows[1][6] = rows[1][6].removeprefix("text:")
    out = io.StringIO(newline="")
    csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(rows)
    changed = out.getvalue().encode()
    if mutation == "lf":
        changed = raw.replace(b"\r\n", b"\n")
    elif mutation == "utf8":
        changed = b"\xff"
    elif mutation == "oversize":
        changed = b" " * (MAX_COMPARISON_BYTES + 1)
    with pytest.raises(EdgeForgeError):
        verify_comparison(source, source, changed, format="csv")


def test_native_retained_workflow_failed_agreement_and_no_execution(
    evidence, tmp_path, monkeypatch, capsys
):
    from edgeforge.benchmark import benchmark
    from edgeforge.contracts import BenchmarkOptions
    from edgeforge.reports import verify_report_bundle

    before = read_source(evidence[2])
    after = read_source(
        benchmark(evidence[1], BenchmarkOptions(warmup=2, iterations=2)).model_dump_json().encode()
    )
    verify_report_bundle(before, evidence[1])
    verify_report_bundle(after, evidence[1])
    data = after.model_dump()
    data["runtime_version"] = "<script>window.bad=true</script>"
    data["agreement"].update(
        passed=False, elements_matching=0, fraction_matching=0.0, max_abs_error=1.0
    )
    after = type(after).model_validate(data)

    def forbidden(*args):
        pytest.fail("offline review must not execute models")

    monkeypatch.setattr("edgeforge.benchmark.create_adapter", forbidden)
    comparison = compare_reports(before, after)
    before_path, after_path, target = [
        tmp_path / n for n in ["before.json", "after.json", "comparison.json"]
    ]
    before_path.write_text(before.model_dump_json(), encoding="utf-8")
    after_path.write_text(after.model_dump_json(), encoding="utf-8")
    target.write_text(comparison.model_dump_json(), encoding="utf-8")

    def call(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    assert call(["comparison-check", target]) == 0
    assert call(["comparison-verify", before_path, after_path, target]) == 0
    csv_path = tmp_path / "comparison.csv"
    csv_path.write_bytes(render_comparison_csv(comparison).encode())
    assert call(["comparison-verify", before_path, after_path, csv_path, "--format", "csv"]) == 0
    html_path = tmp_path / "review.html"
    assert call(["comparison-html", target, "--output", html_path]) == 0
    html = html_path.read_text("utf-8")
    assert html == render_comparison_html(comparison)
    assert "<script" not in html and "&lt;script&gt;" in html
    assert "FAILED" in html and "Incompatible descriptors" in html
    assert "default-src" in html and "sha256-" in html
    assert comparison.before_report_sha256 in html and comparison.after_report_sha256 in html
    capsys.readouterr()
    assert call(["comparison-html", target, "--output", html_path]) == 2
    assert json.loads(capsys.readouterr().err) == {"error": "io_error"}
    original = target.read_bytes()
    target.write_bytes(b"private_marker")
    assert call(["comparison-html", target, "--output", tmp_path / "absent.html"]) == 2
    captured = capsys.readouterr()
    assert not captured.out and json.loads(captured.err) == {"error": "invalid_input"}
    assert not (tmp_path / "absent.html").exists()
    target.write_bytes(original)
    assert before_path.read_text("utf-8") == before.model_dump_json()
    assert after_path.read_text("utf-8") == after.model_dump_json()
