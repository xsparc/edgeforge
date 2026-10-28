# Validation evidence

## EF-001

Acceptance: deterministic bundle roundtrip; reject corrupted models, unexpected
archive entries, duplicate entries, object arrays, nonfinite values, wrong tensor
shapes, and invalid contracts. CLI errors must omit filesystem paths.

Checks are recorded at each slice closeout. No benchmark result is evidence of
performance on an untested device.

2026-10-28: 15 local tests passed on Python 3.12 / Windows, including an oversized
NPY-header rejection before allocation. Ruff lint and formatting passed. Static
and dated strict EdgeForge governance checks passed. The upstream OpenSteward
gate returned one `project.identity` failure, as described below. Hosted platform
checks are defined in CI and are not implied by the local run.

## Governance tooling

The installed OpenSteward checker is specific to its own project identity. Its
unchanged upstream check therefore cannot certify EdgeForge. EdgeForge owns a
project-specific structural gate in `scripts/check_governance.py`; this checks
traceability, repository-local references, approvals, statuses, and review dates.
Both tool outcomes are distinguished in closeout evidence.
