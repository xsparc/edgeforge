import json
import sys
from pathlib import Path

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main, parser, run
from edgeforge.comparison import MAX_COMPARISON_BYTES, compare_reports
from edgeforge.comparison_identity import (
    MAX_IDENTITY_BYTES,
    ComparisonIdentity,
    canonical_comparison,
    read_identity,
    verify_identity_record,
)
from edgeforge.comparison_review import read_source
from edgeforge.errors import EdgeForgeError


def record():
    return {
        "schema_version": 1,
        "canonicalization": "edgeforge-comparison-json-v1",
        "comparison_sha256": "a" * 64,
        "bytes": 100,
        "interpretation": "retained_identity_not_attestation",
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", 2),
        ("canonicalization", "jcs"),
        ("comparison_sha256", "A" * 64),
        ("comparison_sha256", "a" * 64 + "\n"),
        ("comparison_sha256", "z" * 64),
        ("bytes", 0),
        ("bytes", True),
        ("bytes", 100.0),
        ("bytes", MAX_COMPARISON_BYTES + 1),
        ("interpretation", "attested"),
        ("extra", "private"),
    ],
)
def test_closed_identity_contract(key, value):
    data = record()
    data[key] = value
    with pytest.raises((ValueError, EdgeForgeError)):
        read_identity(json.dumps(data).encode())


def test_reader_bounds_duplicates_missing_and_schema():
    valid = record()
    raw = json.dumps(valid).encode()
    assert read_identity(raw).model_dump() == valid
    assert read_identity(raw + b" " * (MAX_IDENTITY_BYTES - len(raw))).model_dump() == valid
    for key in valid:
        bad = dict(valid)
        del bad[key]
        with pytest.raises((ValueError, EdgeForgeError)):
            read_identity(json.dumps(bad).encode())
    for bad in [
        raw.replace(b"{", b'{"schema_version":1,', 1),
        b"\xff",
        b"[]",
        raw + b"{}",
        b"[" * 2000,
        b" " * (MAX_IDENTITY_BYTES + 1),
        b'{"bytes":NaN}',
    ]:
        with pytest.raises((ValueError, EdgeForgeError)):
            read_identity(bad)
    shape = run(parser().parse_args(["comparison-identity-schema"]))
    assert shape == ComparisonIdentity.model_json_schema()
    assert json.loads(Path("schemas/comparison-identity.schema.json").read_text()) == shape
    assert shape["additionalProperties"] is False and set(shape["required"]) == set(valid)


def test_native_retained_identity_workflow(evidence, tmp_path, capsys, monkeypatch):
    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

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
    path, identity = tmp_path / "comparison.json", tmp_path / "identity.json"
    path.write_bytes(raw)
    assert cli(["comparison-identity", path]) == 0
    identity.write_text(capsys.readouterr().out, encoding="utf-8")
    saved = identity.read_bytes()
    retained = read_identity(saved)
    verify_identity_record(comparison, retained)
    assert cli(["comparison-verify-identity", path, identity]) == 0
    assert cli(["comparison-check", path, "--identity", identity]) == 0
    pretty = json.dumps(comparison.model_dump(), indent=4).encode()
    path.write_bytes(pretty)
    for command in ["comparison-html", "comparison-canonical"]:
        output = tmp_path / (command + ".out")
        args = [command, path, "--identity", identity, "--output", output]
        assert cli(args) == 0
        exported = output.read_bytes()
        if command.endswith("canonical"):
            assert exported == raw
        assert cli(args) == 2 and output.read_bytes() == exported
    assert identity.read_bytes() == saved and path.read_bytes() == pretty
    for replacement in [compare_reports(before, before), compare_reports(after, before)]:
        path.write_bytes(canonical_comparison(replacement))
        assert cli(["comparison-check", path]) == 0
        assert cli(["comparison-verify-identity", path, identity]) == 2
        for command in ["comparison-html", "comparison-canonical"]:
            output = tmp_path / ("blocked-" + command)
            assert cli([command, path, "--identity", identity, "--output", output]) == 2
            assert not output.exists()
    path.write_bytes(raw)
    bad = retained.model_dump()
    bad["bytes"] += 1
    identity.write_text(json.dumps(bad))
    assert cli(["comparison-verify-identity", path, identity]) == 2
    identity.write_bytes(b" " * (MAX_IDENTITY_BYTES + 1))
    assert cli(["comparison-verify-identity", path, identity]) == 2
    retained.bytes = 0
    with pytest.raises(ValueError):
        verify_identity_record(comparison, retained)
    assert str(tmp_path) not in capsys.readouterr().err
    for command in ["comparison-check", "comparison-html", "comparison-canonical"]:
        args = [command, str(path), "--identity", str(identity), "--expected-sha256", "a" * 64]
        if command != "comparison-check":
            args += ["--output", str(tmp_path / "never")]
        with pytest.raises(SystemExit) as error:
            parser().parse_args(args)
        assert error.value.code == 2
