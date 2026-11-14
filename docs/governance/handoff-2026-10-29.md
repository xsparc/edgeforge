# Next iteration: directional benchmark comparisons

Status: planned handoff, 2026-10-29. EF-004 implements retained-report validation,
schema export, bundle checks, CSV and the native synthetic workflow. The five
items below are not implemented in that milestone.

1. **Comparison contract.** Define a closed version-1 before/after report model
   with source report digests and signed latency, RSS and storage deltas.
   Keep arithmetic finite and direction explicit; do not infer significance.
2. **Compatibility assessment.** Classify differing bundles, options,
   runtime/provider/thread settings and available platform descriptors with
   fixed reasons. Withhold a performance verdict for incomparable evidence.
   Matching descriptors do not prove identical hardware or measurement conditions.
3. **Bounded comparison CLI and schema.** Compare two strictly validated retained
   reports without inference execution. Preserve byte bounds, sanitized errors
   and exclusive output; export the public comparison schema.
4. **Comparison CSV.** Export direction, evidence identities, compatibility
   reasons and metric deltas with prefixed labels and exact UTF-8/CRLF.
   Test hostile labels, finite arithmetic, numeric round trips and no overwrite.
5. **Comparison acceptance workflow.** Generate synthetic ONNX reports with
   deliberately compatible and mismatched configurations, validate source
   binding, exercise both comparison transports and test reversed direction.
   No timing-based pass/fail or claim of quantization speedup.

Priority: retained reports can now be checked and exported; comparison is the
next local review step before any queued service, physical-device or deployment
work. Review the strict reader's format against real retained reports first.

EF-004 is stacked on MVP PR #3, which depends on #2 and #1. Check their merge
state before selecting the next base. Keep each iteration's implementation,
tests, current-date governance evidence and draft PR together. Merging, releases,
deployment, paid execution and contacting people require separate authorization.
