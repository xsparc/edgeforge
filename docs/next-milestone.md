# Next iteration: retained comparison verification

Status: planned handoff, 2026-10-31. EF-005 completes the
[previous five tasks](governance/handoff-2026-10-29.md).

1. **Bounded comparison reader.** Add a public bytes reader with the comparison
   limit and a read-only comparison-check CLI. Validate nested reports, digests,
   compatibility and arithmetic with sanitized diagnostics and malformed fixtures.
2. **Source-bound comparison verification.** Accept explicit before/after reports
   and retained comparison JSON; recompute and require equality. Reject changed
   snapshots, direction or normalized identities without repairing output.
3. **Source-bound CSV verification.** Verify the exact canonical ten-row export
   against two retained source reports. Enforce UTF-8/CRLF, text prefixes, row and
   column order; reject missing, extra and tampered cells within byte limits.
4. **Script-free HTML review.** Render compatible/incompatible state, fixed reasons,
   source agreement, identities and signed metric tables with escaped text,
   restrictive CSP and bounded exclusive output. Preserve descriptive-only scope.
5. **Portable comparison-review acceptance.** Extend the synthetic native ONNX
   workflow through retained JSON/CSV verification and HTML review; exercise
   reversal, failed agreement and desktop/mobile layouts without timing gates.

Priority: comparison generation is now available; retained evidence needs an
explicit independent checking workflow before any queued service or device work.
EF-005 targets feat/service-interoperability while MVP PR #3 remains open above
#2 and #1. Recheck merge state before branching and avoid duplicating merged work.
These tasks are planned only; merge, release, deployment and paid execution
remain outside the handoff.
