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

## EF-002

2026-10-28: 29 local tests passed, with one native ExecuTorch test skipped because
the runtime is not installed in the Windows development environment. Real ONNX
Runtime 1.31.1 CPU inference and dynamic INT8 MatMul quantization passed. Adapter
contract coverage includes ExecuTorch program loading, positional tensors, and
output conversion. Integer agreement preserves differences beyond float64's exact
range. CLI example generation and a saved benchmark report completed successfully.
Ruff and static/dated strict EdgeForge governance checks passed.

The initial Linux job identified a missing PyTorch dependency. The corrected
environment installs compatible PyTorch and ExecuTorch CPU wheels.
[CI run 40669872522](https://github.com/xsparc/edgeforge/actions/runs/40669872522)
passed all six core platform/Python jobs and both ExecuTorch tests, including
real PyTorch export, PTE loading, and execution. Physical accelerators, mobile
devices, and target-specific delegates have not been tested.

## EF-003

The HTTP integration tests cover bearer authentication, OpenAPI security metadata,
registered bundle hashes, native ONNX measurement, invalid and oversized requests,
changed artifacts, sanitized native failures, worker release, and concurrent-call
backpressure. Governance regression tests verify stale evidence, unknown status,
missing references, and path traversal, including under optimized Python.

The ONNX/API dependency set is pinned with hashes and cross-platform markers.
The wheel and source distribution build successfully. Final integration also
checks scalar tensor preservation and the CLI's accuracy-failure exit code.

2026-10-28 local closeout: 47 tests passed and one native ExecuTorch test was
skipped locally (covered by the passing Linux CI job above). Ruff lint and format,
static and dated strict governance, wheel/source build, installed CLI smoke test,
and archive privacy inspection passed. FastAPI's test client emits an upstream
HTTPX deprecation warning; requests and assertions pass. Final service-branch
platform CI is checked independently after publication.

[Service CI run 40671376506](https://github.com/xsparc/edgeforge/actions/runs/40671376506)
passed all seven jobs: core/ONNX/API tests, lint, schema drift, governance, and
build checks on Windows/macOS/Linux with Python 3.11 and 3.12, plus native
ExecuTorch export and execution on Linux. The initial lock excluded Python 3.11;
regenerating from the minimum supported version added explicit NumPy version
markers, and the full matrix passed. No model performance threshold is inferred
from these functional tests. CI now runs once per PR update, with bounded job
durations, and again on main after merge.
