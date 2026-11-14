import sys

import pytest
from test_comparison_bundle import synthetic

from edgeforge.cli import main
from edgeforge.comparison import render_comparison_csv
from edgeforge.comparison_bundle import create_bundle, encode_bundle, render_bundle, verify_sources
from edgeforge.comparison_review import render_comparison_html
from edgeforge.errors import EdgeForgeError


@pytest.mark.parametrize("format", ["html", "csv"])
def test_independent_bundle_review(tmp_path, monkeypatch, capsys, format):
    a = synthetic()
    data = a.model_dump()
    data["runtime_version"] = "changed"
    b = type(a).model_validate(data)
    bundle = create_bundle(a, b)
    raw = encode_bundle(bundle)
    verify_sources(raw, a, b)
    for left, right in [(b, a), (a, a)]:
        with pytest.raises(EdgeForgeError):
            verify_sources(raw, left, right)
    expected = (
        render_comparison_html(bundle.comparison)
        if format == "html"
        else render_comparison_csv(bundle.comparison)
    ).encode()
    assert render_bundle(bundle, format) == expected
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("inference")
    )
    before, after, retained, out = [tmp_path / n for n in ("a", "b", "bundle", "review")]
    before.write_text(a.model_dump_json())
    after.write_text(b.model_dump_json())
    retained.write_bytes(raw)
    saved = {p: p.read_bytes() for p in (before, after, retained)}

    def cli(args):
        monkeypatch.setattr(sys, "argv", ["edgeforge", *map(str, args)])
        return main()

    verify = ["comparison-bundle-verify", retained]
    sources = ["--before", before, "--after", after]
    assert cli(verify) == 0
    assert cli(verify + sources) == 0
    render = ["comparison-bundle-render", retained, "--format", format, "--output", out]
    for pair in [["--before", before], ["--after", after], ["--before", after, "--after", before]]:
        assert cli(verify + pair) == 2
        assert cli(render + pair) == 2 and not out.exists()
    replacement = encode_bundle(create_bundle(a, a))
    retained.write_bytes(replacement)
    assert cli(verify) == 0
    assert cli(verify + sources) == 2
    assert cli(render + sources) == 2 and not out.exists()
    retained.write_bytes(raw)
    standalone = tmp_path / "standalone"
    assert cli(["comparison-bundle-render", retained, "--output", standalone]) == 0
    assert standalone.read_bytes() == render_comparison_html(bundle.comparison).encode()
    assert cli(render + sources) == 0
    assert out.read_bytes() == expected
    assert cli(render + sources) == 2 and out.read_bytes() == expected
    after.write_bytes(b"x" * (256 * 1024 + 1))
    assert cli(verify + sources) == 2
    after.write_bytes(saved[after])
    assert all(p.read_bytes() == value for p, value in saved.items())
    assert str(tmp_path) not in capsys.readouterr().err


def test_render_bound_and_unsupported_format(monkeypatch):
    bundle = create_bundle(synthetic(), synthetic())
    with pytest.raises(EdgeForgeError):
        render_bundle(bundle, "other")
    monkeypatch.setattr(
        "edgeforge.comparison.render_comparison_csv", lambda _: "x" * (512 * 1024 + 1)
    )
    with pytest.raises(EdgeForgeError):
        render_bundle(bundle, "csv")
