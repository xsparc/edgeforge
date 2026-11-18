import json
import sys

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main
from edgeforge.comparison import compare_reports
from edgeforge.comparison_identity import comparison_identity
from edgeforge.comparison_review import read_source


@pytest.mark.parametrize("format", ["html", "csv"])
def test_source_checked_review_native(evidence, tmp_path, capsys, monkeypatch, format):
    def cli(args):
        if args[0] == "comparison-review":
            args = [*args, "--format", format]
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    before = read_source(evidence[2])
    data = before.model_dump()
    data["runtime_version"] = "<script>injection</script>"
    data["agreement"].update(
        passed=False, elements_matching=0, fraction_matching=0.0, max_abs_error=1.0
    )
    after = type(before).model_validate(data)
    comparison = compare_reports(before, after)
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("execution")
    )
    left, right, retained, identity = [
        tmp_path / name
        for name in ["before.json", "after.json", "comparison.json", "identity.json"]
    ]
    for path, model in [(left, before), (right, after), (retained, comparison)]:
        path.write_text(model.model_dump_json())
    identity.write_text(json.dumps(comparison_identity(comparison)))
    originals = {p: p.read_bytes() for p in [left, right, retained, identity]}
    for gate in [[], ["--identity", identity]]:
        out = tmp_path / ("checked.html" if gate else "sources.html")
        args = ["comparison-review", retained, left, right, "--output", out, *gate]
        assert cli(args) == 0
        html = out.read_bytes()
        if format == "html":
            assert b"<script>" not in html and b"&lt;script&gt;" in html
        else:
            from edgeforge.comparison import render_comparison_csv

            assert html == render_comparison_csv(comparison).encode("utf-8")
        assert cli(args) == 2 and out.read_bytes() == html
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    for a, b in [(left, left), (right, left)]:
        out = tmp_path / "wrong.html"
        assert (
            cli(["comparison-review", retained, a, b, "--identity", identity, "--output", out]) == 2
        )
        assert not out.exists()
    replacement = compare_reports(before, before)
    retained.write_text(replacement.model_dump_json())
    identity.write_text(json.dumps(comparison_identity(replacement)))
    assert cli(["comparison-check", retained, "--identity", identity]) == 0
    out = tmp_path / "replacement.html"
    assert (
        cli(["comparison-review", retained, left, right, "--identity", identity, "--output", out])
        == 2
    )
    assert not out.exists()
    retained.write_bytes(originals[retained])
    identity.write_bytes(b"{}")
    assert (
        cli(["comparison-review", retained, left, right, "--identity", identity, "--output", out])
        == 2
    )
    assert not out.exists()
    right.write_bytes(b" " * (1024 * 1024 + 1))
    assert cli(["comparison-review", retained, left, right, "--output", out]) == 2
    assert not out.exists()
    assert str(tmp_path) not in capsys.readouterr().err


def test_executable_portable_example(tmp_path):
    import runpy

    pytest.importorskip("onnxruntime")
    pytest.importorskip("onnx")
    example = runpy.run_path("examples/portable_review.py")
    result = example["run"](tmp_path / "portable-review")
    assert result["verified"] and result["review_execution"] == "none"


def test_csv_review_output_bound(evidence, tmp_path, monkeypatch):
    source = read_source(evidence[2])
    comparison = compare_reports(source, source)
    left, retained, output = [tmp_path / n for n in ["source.json", "comparison.json", "out.csv"]]
    left.write_text(source.model_dump_json())
    retained.write_text(comparison.model_dump_json())
    monkeypatch.setattr(
        "edgeforge.comparison.render_comparison_csv", lambda c: "x" * (512 * 1024 + 1)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "edgeforge",
            "comparison-review",
            str(retained),
            str(left),
            str(left),
            "--format",
            "csv",
            "--output",
            str(output),
        ],
    )
    assert main() == 2 and not output.exists()
