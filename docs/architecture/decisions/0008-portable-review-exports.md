# ADR 0008: Portable review exports

Status: accepted
Date: 2026-11-10

## Decision

Source-checked comparison review now supports explicit HTML or CSV selection. HTML remains the default; CSV reuses the existing canonical comparison exporter.

```sh
edgeforge comparison-review comparison.json before.json after.json --format csv --identity identity.json --output review.csv
edgeforge comparison-verify before.json after.json review.csv --format csv
```

Both formats verify explicit before/after report sources and any supplied identity record before exclusive creation. Wrong sources still fail when the comparison identity matches. Output is bounded to 512 KiB for both formats; existing input limits and fixed exit-2 diagnostics remain. Failed-agreement evidence is valid descriptive input. Export does not run inference or impose timing thresholds. Existing HTML layout and CSV dialect are unchanged.

## Executable portable acceptance

With the ONNX extra already installed, choose a new destination directory:

```sh
python examples/portable_review.py review-demo
```

The example generates a small ONNX model locally, runs one native benchmark under synthetic capability labels, then deliberately constructs a synthetic failed-agreement after-report. That altered report is a test fixture, not an observed failure. The example writes source reports, comparison and identity records, exports source-checked HTML/CSV, verifies exact CSV bytes, checks non-overwrite behavior, and rejects a consistently replaced comparison plus identity against independent sources.

During the review phase, adapter creation is replaced with a failure guard: any attempted inference fails the example. The result is a fixed JSON acceptance summary. The destination must not already exist. Generated benchmark values are local evidence, not portable performance claims; no private paths or actual environment labels are emitted by the example. Review files do not authenticate authorship or establish device equivalence.

## Alternatives and acceptance

Reuse semantic validators and canonical exporters. Do not repair CSV or let a
matching identity substitute for matching explicit sources. Retain existing
formats and runtime boundaries. Acceptance covers exact bytes, direction,
consistent replacement, bounds, formula-safe text, exclusive output and no
review-time execution. No HTML layout changes are introduced in this slice.
