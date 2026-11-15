import hashlib
import json
import sys

import pytest
from test_comparison_bundle import synthetic

from edgeforge.cli import main
from edgeforge.comparison_bundle import (
    bundle_identity,
    create_bundle,
    encode_bundle,
    read_bundle,
    render_bundle,
    verify_export,
    verify_identity,
)
from edgeforge.errors import EdgeForgeError


def pair():
    a = synthetic()
    data = a.model_dump()
    data["runtime_version"] = "changed"
    return a, type(a).model_validate(data)


def test_normalized_identity_and_strict_digest():
    a, b = pair()
    bundle = create_bundle(a, b)
    raw = encode_bundle(bundle)
    record = bundle_identity(bundle)
    assert record["bundle_sha256"] == (
        "73e8de939468e4be371d6c9cfc42ccbbf7dc7747f1e789e5f9f8fb6e9b71cadc"
    )
    assert record["bytes"] == 6072
    assert record["bundle_sha256"] == hashlib.sha256(raw).hexdigest()
    assert record["bytes"] == len(raw)
    pretty = json.dumps(bundle.model_dump(), indent=2).encode()
    assert bundle_identity(read_bundle(pretty)) == record
    assert hashlib.sha256(pretty).hexdigest() != record["bundle_sha256"]
    assert bundle_identity(create_bundle(b, a)) != record
    assert bundle_identity(create_bundle(a, a)) != record
    verify_identity(bundle, record["bundle_sha256"])
    for bad in [
        "",
        "0" * 64,
        record["bundle_sha256"].upper(),
        "g" * 64,
        record["bundle_sha256"] + "\n",
    ]:
        with pytest.raises(EdgeForgeError):
            verify_identity(bundle, bad)


@pytest.mark.parametrize("format", ["html", "csv"])
def test_exact_export_identity_and_sources(tmp_path, monkeypatch, capsys, format):
    a, b = pair()
    bundle = create_bundle(a, b)
    export = render_bundle(bundle, format)
    verify_export(bundle, export, format)
    for bad in [export + b"\n", b"\xff", b"x" * (512 * 1024 + 1)]:
        with pytest.raises(EdgeForgeError):
            verify_export(bundle, bad, format)
    if format == "html":
        for bad in [
            export.replace(b"style", b"STYLE"),
            export.replace(b"Content-Security-Policy", b"Removed-Security-Policy"),
        ]:
            with pytest.raises(EdgeForgeError):
                verify_export(bundle, bad, format)
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("inference")
    )
    left, right, retained, output = [tmp_path / n for n in ("a", "b", "bundle", "export")]
    left.write_text(a.model_dump_json())
    right.write_text(b.model_dump_json())
    retained.write_bytes(encode_bundle(bundle))
    output.write_bytes(export)
    saved = {p: p.read_bytes() for p in (left, right, retained, output)}
    digest = bundle_identity(bundle)["bundle_sha256"]

    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    assert cli(["comparison-bundle-identity", retained]) == 0
    assert json.loads(capsys.readouterr().out)["bundle_sha256"] == digest
    base = ["comparison-bundle-verify-export", retained, output, "--format", format]
    sources = ["--before", left, "--after", right]
    assert cli(base) == 0
    assert cli(base + sources + ["--expected-sha256", digest]) == 0
    assert cli(base + ["--expected-sha256", "0" * 64]) == 2
    assert cli(base + ["--before", left]) == 2
    assert cli(base + ["--before", right, "--after", left]) == 2
    blocked = tmp_path / "blocked"
    assert (
        cli(
            [
                "comparison-bundle-render",
                retained,
                "--output",
                blocked,
                "--expected-sha256",
                "0" * 64,
            ]
        )
        == 2
    )
    assert not blocked.exists()
    assert cli(["comparison-bundle-verify", retained, "--expected-sha256", digest]) == 0
    replacement = create_bundle(a, a)
    retained.write_bytes(encode_bundle(replacement))
    output.write_bytes(render_bundle(replacement, format))
    gate = ["--expected-sha256", bundle_identity(replacement)["bundle_sha256"]]
    assert cli(base + gate) == 0
    assert cli(base + gate + sources) == 2
    for p, raw in saved.items():
        p.write_bytes(raw)
    assert cli(base + sources + ["--expected-sha256", digest]) == 0
    assert all(p.read_bytes() == raw for p, raw in saved.items())
    assert str(tmp_path) not in capsys.readouterr().err
