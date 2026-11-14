# Retained benchmark report review

Status: accepted, 2026-10-29. EF-004 initializes five tasks under the requested
next-milestone iteration: report validation, schema, bundle checks, CSV export
and native acceptance coverage.

Add a strict reader for existing version-1 benchmark JSON. ReportEvidence closes
nested latency, memory, storage, agreement and capability fields, bounds labels,
requires integer versions and finite/nonnegative measurements, and checks
percentile order, RSS arithmetic, agreement fractions/verdicts, timestamp zones
and invocation counts. Existing benchmark SDK/API output and its schema remain
unchanged; report-evidence.schema.json describes the stricter retained reader.

report-check reads at most 256 KiB, emits only fixed summary fields and accepts
failed agreement as valid evidence. Optional --bundle verifies its digest,
runtime/provider/thread configuration, storage sizes, cases and compared element
count using bundle validation without loading any native model adapter.
report-schema exports the reader schema. report-csv exports one quoted row with
text-prefixed free-text labels, exact UTF-8/CRLF and exclusive file creation.

A synthetic ONNX acceptance fixture benchmarks the built-in model, validates the
report, checks it against the retained bundle and round-trips CSV via the CLI.
It substitutes synthetic capability labels and checks tampering, malformed or
oversized files, inconsistent arithmetic, path-free errors and non-overwrite.
Existing CI runs this fixture with real ONNX Runtime on all supported hosts.

Local consistency cannot prove a report's measurements or origin. No timing
regression verdict, task accuracy, cross-device prediction, signatures, runtime
sandbox, service endpoint or device deployment is introduced. Reports remain
trusted local evidence. A stricter reader can reject previously hand-edited
reports that do not satisfy the emitted format; the producer is unchanged.
