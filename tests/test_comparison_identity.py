import hashlib
import json
import sys

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main as cli_main
from edgeforge.comparison import compare_reports
from edgeforge.comparison_identity import (
    canonical_comparison,
    comparison_identity,
    verify_expected_identity,
)
from edgeforge.comparison_review import read_comparison, read_source
from edgeforge.errors import EdgeForgeError


def test_canonical_identity_native_retention(evidence, tmp_path, capsys, monkeypatch):
    def main(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *args])
        return cli_main()

    before = read_source(evidence[2])
    data = before.model_dump()
    data["runtime_version"] = "synthetic-next"
    data["agreement"].update(
        passed=False, elements_matching=0, fraction_matching=0.0, max_abs_error=1.0
    )
    after = type(before).model_validate(data)
    comparison = compare_reports(before, after)
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("execution")
    )
    raw = canonical_comparison(comparison)
    identity = comparison_identity(comparison)
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert identity["comparison_sha256"] == hashlib.sha256(raw).hexdigest()
    assert identity["bytes"] == len(raw)
    pretty = json.dumps(comparison.model_dump(), indent=4).encode()
    assert canonical_comparison(read_comparison(pretty)) == raw
    assert hashlib.sha256(pretty).hexdigest() != identity["comparison_sha256"]
    for replaced in [compare_reports(before, before), compare_reports(after, before)]:
        assert read_comparison(canonical_comparison(replaced)) == replaced
        with pytest.raises(EdgeForgeError):
            verify_expected_identity(replaced, identity["comparison_sha256"])
    source, output = tmp_path / "retained.json", tmp_path / "canonical.json"
    source.write_bytes(pretty)
    assert main(["comparison-identity", str(source)]) == 0
    assert json.loads(capsys.readouterr().out) == identity
    args = [
        "comparison-canonical",
        str(source),
        "--output",
        str(output),
        "--expected-sha256",
        identity["comparison_sha256"],
    ]
    assert main(args) == 0
    assert output.read_bytes() == raw
    assert main(args) == 2 and output.read_bytes() == raw
    for command in ["comparison-check", "comparison-html", "comparison-canonical"]:
        target = tmp_path / (command + ".out")
        args = [command, str(source), "--expected-sha256", "0" * 64]
        if command != "comparison-check":
            args += ["--output", str(target)]
        assert main(args) == 2 and not target.exists()
    assert (
        main(["comparison-check", str(source), "--expected-sha256", identity["comparison_sha256"]])
        == 0
    )
    assert source.read_bytes() == pretty
    invalid = comparison.model_dump()
    invalid["schema_version"] = 2
    for bad in [json.dumps(invalid).encode(), b" " * (512 * 1024 + 1)]:
        source.write_bytes(bad)
        target = tmp_path / "invalid-export.json"
        assert main(["comparison-canonical", str(source), "--output", str(target)]) == 2
        assert not target.exists()
    assert str(tmp_path) not in capsys.readouterr().err


@pytest.mark.parametrize("expected", ["", "0" * 63, "A" * 64, "z" * 64, "../private"])
def test_expected_identity_strict(evidence, expected):
    source = read_source(evidence[2])
    with pytest.raises(EdgeForgeError):
        verify_expected_identity(compare_reports(source, source), expected)


def test_mutated_sdk_and_export_bound(evidence, monkeypatch):
    source = read_source(evidence[2])
    comparison = compare_reports(source, source)
    monkeypatch.setattr("edgeforge.comparison_identity.MAX_COMPARISON_BYTES", 1)
    with pytest.raises(EdgeForgeError):
        canonical_comparison(comparison)
    monkeypatch.undo()
    comparison.before.options.__dict__["iterations"] = 0
    with pytest.raises((ValueError, EdgeForgeError)):
        canonical_comparison(comparison)
