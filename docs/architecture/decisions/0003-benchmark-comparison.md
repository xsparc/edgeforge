# Descriptive benchmark comparisons

Status: accepted, 2026-10-31. EF-005 implements the five retained comparison tasks.

Define a closed v1 ReportComparison with strict retained before/after reports,
canonical source digests, signed after-minus-before latency/RSS/storage deltas,
compatibility and fixed ordered reasons. Recompute digests, reasons and deltas
on model validation, including when SDK callers supply mutated model instances.
Reject non-finite arithmetic and unsupported fields/versions.

Digest normalized report model JSON, sorted keys, compact separators, escaped
non-ASCII characters and UTF-8 encoding. This binds semantic retained evidence,
not the original file formatting. Differences in bundle, options, runtime/version,
requested/active provider, threads, cases, device descriptors or producer version
produce fixed reasons. Different timestamps and measured values are expected.

Matching descriptors do not establish hardware identity. Always withhold a
performance verdict, including for compatible reports; deltas are descriptive
and do not establish significance, causation, accuracy or quantization benefit.
Source agreement and scope remain visible in full snapshots, including failures.

The offline CLI reads each source within 256 KiB, bounds output to 512 KiB,
creates files exclusively and sanitizes errors. Schema export describes the
comparison model; cross-field arithmetic additionally requires model validation.
CSV uses ten metric rows with identities, reasons, direction and prefixed free
text, quoted UTF-8/CRLF bytes. No service endpoint or native execution is added.

Acceptance benchmarks a synthetic ONNX bundle with equal and changed options,
checks source bundle binding and reversal, and exercises both transports. CI
includes these tests in the existing native ONNX matrix. Timing is never a gate.
