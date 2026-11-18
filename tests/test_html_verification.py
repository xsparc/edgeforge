import json
import sys

import pytest
from test_reports import evidence as evidence

from edgeforge.cli import main
from edgeforge.comparison import MAX_COMPARISON_BYTES, compare_reports
from edgeforge.comparison_identity import comparison_identity
from edgeforge.comparison_review import read_source, render_comparison_html, verify_comparison_html
from edgeforge.errors import EdgeForgeError


def test_exact_html_sources_and_identity(evidence, tmp_path, monkeypatch, capsys):
    a = read_source(evidence[2])
    data = a.model_dump()
    data["runtime_version"] = "synthetic-after"
    b = type(a).model_validate(data)
    comparison = compare_reports(a, b)
    html = render_comparison_html(comparison).encode()
    verify_comparison_html(comparison, html)
    for changed in [
        html + b"\n",
        html.replace(b"style", b"STYLE"),
        html.replace(b"Content-Security-Policy", b"Removed-Security-Policy"),
        html.replace(b"<", b"[", 1),
        b"\xff",
        b"x" * (MAX_COMPARISON_BYTES + 1),
    ]:
        with pytest.raises(EdgeForgeError):
            verify_comparison_html(comparison, changed)
    left, right, retained, identity, output = [
        tmp_path / n for n in ("a.json", "b.json", "retained.json", "id.json", "review.html")
    ]
    for path, model in [(left, a), (right, b), (retained, comparison)]:
        path.write_text(model.model_dump_json())
    identity.write_text(json.dumps(comparison_identity(comparison)))
    output.write_bytes(html)
    saved = {p: p.read_bytes() for p in (left, right, retained, identity, output)}
    monkeypatch.setattr(
        "edgeforge.benchmark.create_adapter", lambda *a, **k: pytest.fail("execution")
    )

    def cli(before=left, after=right, gate=True):
        args = ["edgeforge", "comparison-verify-html", retained, before, after, output]
        if gate:
            args += ["--identity", identity]
        monkeypatch.setattr(sys, "argv", list(map(str, args)))
        return main()

    assert cli() == 0
    assert cli(gate=False) == 0
    assert cli(right, left) == 2
    assert cli(left, left) == 2
    replacement = compare_reports(a, a)
    retained.write_text(replacement.model_dump_json())
    identity.write_text(json.dumps(comparison_identity(replacement)))
    output.write_bytes(render_comparison_html(replacement).encode())
    assert cli(left, left) == 0
    assert cli() == 2
    for p, raw in saved.items():
        p.write_bytes(raw)
    output.write_bytes(html + b"\n")
    assert cli() == 2
    output.write_bytes(b"x" * (MAX_COMPARISON_BYTES + 1))
    assert cli() == 2
    output.write_bytes(html)
    assert all(p.read_bytes() == raw for p, raw in saved.items())
    assert str(tmp_path) not in capsys.readouterr().err
