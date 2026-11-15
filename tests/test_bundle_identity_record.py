import json
import runpy
import sys
from pathlib import Path

import pytest
from test_bundle_identity_export import pair

from edgeforge.bundle_identity import (
    MAX_IDENTITY_BYTES,
    BundleIdentity,
    read_identity,
    verify_identity_record,
)
from edgeforge.cli import main, parser
from edgeforge.comparison_bundle import (
    MAX_COMPARISON_BUNDLE_BYTES,
    bundle_identity,
    create_bundle,
    encode_bundle,
    render_bundle,
)
from edgeforge.errors import EdgeForgeError


def test_closed_identity_reader_and_schema():
    bundle = create_bundle(*pair())
    record = bundle_identity(bundle)
    raw = json.dumps(record).encode()
    assert read_identity(raw).model_dump() == record
    assert (
        record["bundle_sha256"]
        == "73e8de939468e4be371d6c9cfc42ccbbf7dc7747f1e789e5f9f8fb6e9b71cadc"
    )
    assert record["bytes"] == 6072
    schema = BundleIdentity.model_json_schema()
    assert (
        json.loads(
            Path("schemas/comparison-bundle-identity.schema.json").read_text(encoding="utf-8")
        )
        == schema
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(record)
    assert schema["properties"]["bytes"]["maximum"] == MAX_COMPARISON_BUNDLE_BYTES
    assert read_identity(raw + b" " * (MAX_IDENTITY_BYTES - len(raw))).model_dump() == record
    invalid = [
        b"[]",
        b"\xff",
        raw + b"{}",
        b" " * 4097,
        raw.replace(b"{", b'{"schema_version":1,', 1),
    ]
    for key in record:
        invalid.append(json.dumps({k: v for k, v in record.items() if k != key}).encode())
    for key, value in [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("schema_version", 2),
        ("encoding", "jcs"),
        ("bundle_sha256", "A" * 64),
        ("bundle_sha256", "a" * 64 + "\n"),
        ("bundle_sha256", "g" * 64),
        ("bytes", True),
        ("bytes", 1.0),
        ("bytes", 0),
        ("bytes", MAX_COMPARISON_BUNDLE_BYTES + 1),
        ("interpretation", "attested"),
        ("extra", 1),
    ]:
        invalid.append(json.dumps({**record, key: value}).encode())
    for bad in invalid:
        with pytest.raises((ValueError, EdgeForgeError)):
            read_identity(bad)
    identity = read_identity(raw)
    verify_identity_record(bundle, identity)
    identity.bytes += 1
    with pytest.raises(EdgeForgeError):
        verify_identity_record(bundle, identity)
    identity.bytes = True
    with pytest.raises(ValueError):
        verify_identity_record(bundle, identity)


@pytest.mark.parametrize("format", ["html", "csv"])
def test_cli_identity_gates_and_exclusive_export(tmp_path, monkeypatch, capsys, format):
    a, b = pair()
    bundle = create_bundle(a, b)
    path, identity, export, left, right = [
        tmp_path / n for n in ("bundle", "identity", "export", "a", "b")
    ]
    path.write_bytes(encode_bundle(bundle))
    export.write_bytes(render_bundle(bundle, format))
    left.write_text(a.model_dump_json())
    right.write_text(b.model_dump_json())
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("inference")
    )

    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    assert cli(["comparison-bundle-identity-schema"]) == 0
    assert json.loads(capsys.readouterr().out) == BundleIdentity.model_json_schema()
    assert cli(["comparison-bundle-identity", path, "--output", identity]) == 0
    assert capsys.readouterr().out == ""
    saved = {p: p.read_bytes() for p in (path, identity, export, left, right)}
    assert cli(["comparison-bundle-identity", path, "--output", identity]) == 2
    args = [
        "comparison-bundle-verify-export",
        path,
        export,
        "--format",
        format,
        "--identity",
        identity,
    ]
    sources = ["--before", left, "--after", right]
    assert cli(args + sources) == 0
    assert cli(["comparison-bundle-verify", path, "--identity", identity, *sources]) == 0
    output = tmp_path / "rendered"
    assert (
        cli(
            [
                "comparison-bundle-render",
                path,
                "--format",
                format,
                "--output",
                output,
                "--identity",
                identity,
                *sources,
            ]
        )
        == 0
    )
    assert output.read_bytes() == saved[export]
    for command in (
        "comparison-bundle-verify",
        "comparison-bundle-render",
        "comparison-bundle-verify-export",
    ):
        tail = (
            ["--output", tmp_path / "blocked"]
            if command.endswith("render")
            else ([export, "--format", format] if command.endswith("export") else [])
        )
        with pytest.raises(SystemExit):
            parser().parse_args(
                list(
                    map(
                        str,
                        [
                            command,
                            path,
                            *tail,
                            "--identity",
                            identity,
                            "--expected-sha256",
                            "0" * 64,
                        ],
                    )
                )
            )
    identity.write_bytes(b"{}")
    assert cli(args) == 2
    assert (
        cli(
            [
                "comparison-bundle-render",
                path,
                "--output",
                tmp_path / "blocked",
                "--identity",
                identity,
            ]
        )
        == 2
    )
    assert not (tmp_path / "blocked").exists()
    replacement = create_bundle(a, a)
    path.write_bytes(encode_bundle(replacement))
    export.write_bytes(render_bundle(replacement, format))
    identity.write_bytes(json.dumps(bundle_identity(replacement)).encode())
    assert cli(args) == 0
    assert cli(args + sources) == 2
    for p, raw in saved.items():
        p.write_bytes(raw)
    assert cli(args + sources) == 0
    assert all(p.read_bytes() == raw for p, raw in saved.items())
    assert str(tmp_path) not in capsys.readouterr().err
    path.write_bytes(b"{}")
    assert cli(["comparison-bundle-identity", path, "--output", tmp_path / "invalid"]) == 2
    assert not (tmp_path / "invalid").exists()


def test_portable_bundle_workflow(tmp_path):
    example = runpy.run_path("examples/bundle_review.py")
    assert example["run"](tmp_path / "review") == {
        "verified": True,
        "formats": ["html", "csv"],
        "inference": "none",
    }
