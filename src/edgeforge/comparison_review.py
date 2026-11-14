"""Bounded retained comparison intake, source verification and script-free review."""

import base64
import csv
import hashlib
import io
import json
from html import escape

from .comparison import (
    MAX_COMPARISON_BYTES,
    ReportComparison,
    compare_reports,
    render_comparison_csv,
)
from .errors import EdgeForgeError
from .reports import MAX_REPORT_BYTES, ReportEvidence


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate field")
        value[key] = item
    return value


def _constant(value):
    raise ValueError("non-finite JSON")


def _decode(raw: bytes, limit: int):
    if len(raw) > limit:
        raise EdgeForgeError("evidence exceeds byte limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
        # Reject lone Unicode surrogates before they can reach a UTF-8 renderer.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return value
    except (ValueError, RecursionError) as exc:
        raise EdgeForgeError("invalid evidence JSON") from exc


def read_source(raw: bytes) -> ReportEvidence:
    return ReportEvidence.model_validate(_decode(raw, MAX_REPORT_BYTES))


def read_comparison(raw: bytes) -> ReportComparison:
    data = _decode(raw, MAX_COMPARISON_BYTES)
    if not isinstance(data, dict) or set(data) != set(ReportComparison.model_fields):
        raise EdgeForgeError("incomplete comparison envelope")
    return ReportComparison.model_validate(data)


def verify_comparison(
    before: ReportEvidence, after: ReportEvidence, raw: bytes, *, format: str = "json"
) -> ReportComparison:
    expected = compare_reports(before, after)
    if len(raw) > MAX_COMPARISON_BYTES:
        raise EdgeForgeError("comparison exceeds byte limit")
    if format == "json":
        if read_comparison(raw) != expected:
            raise EdgeForgeError("comparison differs from sources")
    elif format == "csv":
        canonical = render_comparison_csv(expected).encode("utf-8")
        try:
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True))
            expected_rows = list(csv.reader(io.StringIO(canonical.decode("utf-8"), newline="")))
        except (UnicodeError, csv.Error) as exc:
            raise EdgeForgeError("invalid comparison CSV") from exc
        if rows != expected_rows or raw != canonical:
            raise EdgeForgeError("comparison differs from canonical sources")
    else:
        raise EdgeForgeError("unsupported comparison format")
    return expected


STYLE = """body{margin:0;background:#f3f6f8;color:#203345;font:16px/1.5 system-ui}
main{max-width:1100px;margin:auto;padding:20px}section{background:white;border:1px solid #ccd9e2;
border-radius:10px;padding:18px;margin:20px 0}h1{line-height:1.2}code{overflow-wrap:anywhere}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;
padding:10px;border-bottom:1px solid #ccd9e2}h2,h3,p{overflow-wrap:anywhere}
@media(max-width:600px){main{padding:12px}section{padding:12px}th,td{padding:7px}}"""


def render_comparison_html(comparison: ReportComparison) -> str:
    comparison = ReportComparison.model_validate(comparison.model_dump())
    digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    csp = f"default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'sha256-{digest}'"
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{escape(csp, quote=True)}">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>Benchmark comparison</title><style>{STYLE}</style></head><body><main>",
        "<p>EdgeForge / Retained evidence</p><h1>Benchmark comparison</h1>",
        "<p>Changes are after minus before. These values are descriptive; no performance "
        "verdict or statistical significance is established. Matching descriptors do not "
        "establish identical hardware or measurement conditions.</p>",
        "<section><h2>Compatibility</h2>",
        "<p>"
        + ("Compatible descriptors" if comparison.compatible else "Incompatible descriptors")
        + "</p>",
        "<p>Reasons: " + escape(", ".join(comparison.incompatibility_reasons) or "none") + "</p>",
        "<p>Hardware identity: not established. Local consistency is not measurement "
        "attestation.</p></section>",
    ]
    for label, report, identity in [
        ("Before", comparison.before, comparison.before_report_sha256),
        ("After", comparison.after, comparison.after_report_sha256),
    ]:
        parts += [
            f"<section><h2>{label}</h2>",
            f"<p>Report SHA-256<br><code>{identity}</code></p>",
            f"<p>Bundle SHA-256<br><code>{report.bundle_sha256}</code></p>",
            f"<p>Runtime: {escape(report.runtime)} / {escape(report.runtime_version)}</p>",
            f"<p>Measured at: {escape(report.measured_at)}</p>",
            f"<p>Golden-output agreement: {'passed' if report.agreement.passed else 'FAILED'}; "
            f"finite: {str(report.agreement.finite).lower()}; "
            f"{report.agreement.elements_matching}/{report.agreement.elements_compared} "
            "elements.</p>",
            "<p>Golden-output agreement is not task-level accuracy.</p>",
            f"<p>{escape(report.measurement_scope)}</p></section>",
        ]
    for group, title, changes in [
        ("latency_ms", "Latency (ms)", comparison.latency_ms_delta),
        ("memory", "Whole-process RSS (bytes)", comparison.memory_delta),
        ("storage", "Storage (bytes)", comparison.storage_delta),
    ]:
        parts.append(
            f'<section><h2>{title}</h2><div class="table-wrap"><table><thead><tr>'
            '<th scope="col">Metric</th><th scope="col">Before</th>'
            '<th scope="col">After</th><th scope="col">Change</th></tr></thead><tbody>'
        )
        for name, change in changes.model_dump().items():
            parts.append(
                f'<tr><th scope="row">{escape(name)}</th>'
                f"<td>{getattr(getattr(comparison.before, group), name)}</td>"
                f"<td>{getattr(getattr(comparison.after, group), name)}</td>"
                f"<td>{change:+}</td></tr>"
            )
        parts.append("</tbody></table></div></section>")
    parts.append("</main></body></html>")
    output = "".join(parts)
    if len(output.encode("utf-8")) > MAX_COMPARISON_BYTES:
        raise EdgeForgeError("rendered comparison exceeds byte limit")
    return output


def verify_comparison_html(comparison, raw: bytes) -> None:
    if len(raw) > MAX_COMPARISON_BYTES:
        raise EdgeForgeError("HTML exceeds byte limit")
    checked = read_comparison(comparison.model_dump_json().encode("utf-8"))
    expected = render_comparison_html(checked).encode("utf-8")
    if len(expected) > MAX_COMPARISON_BYTES or raw != expected:
        raise EdgeForgeError("HTML differs from canonical rendering")
