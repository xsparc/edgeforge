import json
import sys

from test_bundle_identity_export import pair

from edgeforge.cli import main
from edgeforge.comparison_bundle import bundle_identity, create_bundle, encode_bundle, render_bundle


def test_bundle_scope_and_identity_check(tmp_path, monkeypatch, capsys):
    a, b = pair()
    bundle = create_bundle(a, b)
    left, right, path, record = [tmp_path / n for n in ("a", "b", "bundle", "identity")]
    left.write_text(a.model_dump_json())
    right.write_text(b.model_dump_json())
    path.write_bytes(encode_bundle(bundle))
    identity = bundle_identity(bundle)
    raw = json.dumps(identity).encode()
    record.write_bytes(raw)

    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    assert cli(["comparison-bundle-identity-check", record]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "valid": True,
        "interpretation": "identity_record_validity_only",
    }
    for bad in [
        b"{}",
        b"[]",
        raw.replace(b"{", b'{"schema_version":1,', 1),
        b" " * 4097,
        json.dumps({**identity, "bytes": True}).encode(),
    ]:
        record.write_bytes(bad)
        assert cli(["comparison-bundle-identity-check", record]) == 2
        assert not capsys.readouterr().out and record.read_bytes() == bad
    record.write_bytes(raw)
    commands = [["comparison-bundle-verify", path]]
    for format in ("html", "csv"):
        export = tmp_path / format
        export.write_bytes(render_bundle(bundle, format))
        commands.append(["comparison-bundle-verify-export", path, export, "--format", format])
    saved = {p: p.read_bytes() for p in tmp_path.iterdir()}
    for args in commands:
        for sources in [[], ["--before", left, "--after", right]]:
            for gate in [
                [],
                ["--identity", record],
                ["--expected-sha256", identity["bundle_sha256"]],
            ]:
                assert cli(args + sources + gate) == 0
                result = json.loads(capsys.readouterr().out)
                assert result["source_checked"] is bool(sources)
                assert result["identity_checked"] is bool(gate)
            assert cli(args + sources + ["--expected-sha256", "0" * 64]) == 2
            assert not capsys.readouterr().out
    assert all(p.read_bytes() == raw for p, raw in saved.items())
    replacement = create_bundle(a, a)
    path.write_bytes(encode_bundle(replacement))
    record.write_text(json.dumps(bundle_identity(replacement)))
    assert cli(["comparison-bundle-verify", path, "--identity", record]) == 0
    assert json.loads(capsys.readouterr().out)["source_checked"] is False
    assert (
        cli(
            [
                "comparison-bundle-verify",
                path,
                "--identity",
                record,
                "--before",
                left,
                "--after",
                right,
            ]
        )
        == 2
    )
    assert not capsys.readouterr().out
