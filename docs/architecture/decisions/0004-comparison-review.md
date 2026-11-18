# Retained comparison review

Status: accepted, 2026-11-04. EF-006 completes the five saved review tasks.

Add a 512 KiB retained comparison reader. Require all emitted top-level fields
and validate the closed model, nested reports, digests, reasons and deltas.
Reject duplicate keys, invalid UTF-8, lone surrogates, nonfinite JSON and excessive
nesting. Explicit source reports remain bounded to 256 KiB each.

comparison-check proves internal consistency. comparison-verify accepts explicit
before/after reports and requires retained JSON to equal a newly computed
comparison. CSV verification parses and requires the exact canonical quoted
UTF-8/CRLF export, including text: prefixes and row order. No normalization or
repair occurs. Self-consistent replacement fails against independently retained
original sources.

comparison-html validates retained JSON before exclusive output creation. Render
compatibility/reasons, source identities, golden-output agreement and signed
latency/RSS/storage tables. Escape text, use a restrictive meta CSP with a fixed
stylesheet hash, and bound output to 512 KiB. Tables scroll within their mobile
container. Failed agreement remains visible and does not make evidence malformed.
No script, remote resource, model or service executes during these commands.

Acceptance uses real synthetic ONNX reports with changed options plus deliberately
failed retained agreement, both verifier transports, reversal, tampering, bounded
input and exclusive output. Browser checks cover desktop/mobile layouts. Evidence
remains descriptive: no performance verdict, significance, authorship, hardware
identity or measurement attestation is established.
