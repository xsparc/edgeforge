# Design history

## 2026-10-29: EF-004

Retained benchmark report review: decision docs/architecture/decisions/0002-retained-report-review.md; validation docs/governance/report-review-validation.md.

## 2026-10-31: EF-005

Descriptive benchmark comparisons: decision `docs/architecture/decisions/0003-benchmark-comparison.md`; verification `docs/governance/benchmark-comparison-validation.md`.

## 2026-11-02: EF-003 dependency correction

Raised the optional ONNX minimum to 1.22 to exclude affected versions described
in four ONNX advisories; retained the patched 1.23.2 lock. Validation and limits:
`docs/governance/2026-11-02-dependency-validation.md`. Architecture, runtime
selection, and the planned next milestone are unchanged.

## 2026-11-04: EF-006

Retained comparison review: `docs/architecture/decisions/0004-comparison-review.md`; verification `docs/governance/comparison-review-validation.md`.

## EF-007: Canonical comparisons (2026-11-05)

Completed the saved milestone with bounded, non-executing retained-evidence checks.
See `docs/architecture/decisions/0005-canonical-comparisons.md`, `docs/canonical-comparisons.md` and `docs/governance/canonical-comparisons-validation.md`.
The next five tasks in `docs/next-milestone.md` are planned only.

## EF-008: Retained identities (2026-11-07)

Implemented the saved retained-evidence tasks. Decision: `docs/architecture/decisions/0006-retained-identities.md`.
Workflow and limits: `docs/retained-identities.md`. Verification: `docs/governance/retained-identities-validation.md`.
The shared next-five project tracker is `docs/next-milestone.md`; its tasks remain planned.
