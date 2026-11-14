# Compare retained benchmark reports

```console
edgeforge report-check before.json --bundle model.efb
edgeforge report-check after.json --bundle model.efb
edgeforge report-compare before.json after.json --output comparison.json
edgeforge report-compare before.json after.json --format csv --output comparison.csv
edgeforge comparison-schema
```

Reports must satisfy the strict retained-report reader. The comparison preserves
both complete snapshots, including golden-output agreement and measurement scope.
Signed deltas always mean after minus before. Negative latency or RSS changes
are descriptive values, not proof of a performance improvement.

Compatibility reasons, in order: bundle, options, runtime, runtime_version,
requested_provider, active_providers, threads, cases, device, edgeforge_version.
All available device descriptors and package versions are compared. Empty reasons
mean matching descriptors only; hardware_identity remains not_established and
interpretation remains descriptive_only_no_performance_verdict. Failed numerical
agreement is retained as evidence and must be considered by the reviewer.

Report identities hash normalized model JSON with sorted keys, compact separators
and escaped non-ASCII text, encoded as UTF-8. Formatting changes do not change
identity. This is local consistency, not measurement attestation or authorship.
The SDK ReportComparison reader verifies its source digests and derived fields;
the JSON Schema describes shape and cannot alone verify arithmetic.

Each source is limited to 256 KiB and output to 512 KiB. Files are created
exclusively, never replaced. CSV stdout and files use identical quoted UTF-8/CRLF;
ten rows cover five latency, three whole-process RSS and two storage metrics.
Runtime version labels have a literal text: prefix to prevent formula handling.
Compatible and incompatible comparisons exit 0 because no performance gate is
applied. Invalid input exits 2 with a fixed diagnostic and no source path echo.

For a native acceptance example, generate the built-in model with `edgeforge
example demo`, pack its assets as described in the README, and benchmark the same
bundle twice with equal options. Change warmup on a third report to produce an
options mismatch. Compare in both directions; do not assert a timing threshold.
`tests/test_comparison.py` automates this with synthetic capability descriptors,
real ONNX Runtime, bundle checks and read-only JSON/CSV export.
