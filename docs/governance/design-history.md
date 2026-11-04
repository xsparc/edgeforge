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
