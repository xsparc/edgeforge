# EF-003 ONNX dependency correction

Scope: require `onnx>=1.22,<2` in the ONNX extra, retaining the hashed 1.23.2
lock. This is a dependency correction under the authorized maintenance of the
three-PR MVP. It changes neither bundle/report contracts nor runtime selection.
The advisory ranges and release review are recorded in
[the direction brief](../research/2026-11-02-runtime-security.md).

Acceptance: built wheel metadata rejects the affected ONNX versions and accepts
1.22.0 and the pinned 1.23.2; current ONNX inference and dynamic quantization,
full integration tests, lint/format and governance checks pass. Do not claim a
new supported runtime pair, device validation, or a complete dependency audit.

## Local validation: 2026-11-02

- Targeted native ONNX tests: 6 passed, including CPU inference and dynamic INT8
  quantization with ONNX 1.23.2 and ONNX Runtime 1.31.1.
- Full suite: 86 passed, 1 native ExecuTorch test skipped because the runtime is
  unavailable in this Windows environment. The existing Starlette/httpx test
  client deprecation warning remains.
- Ruff lint and format: passed (49 Python files).
- Static and dated strict EdgeForge governance: passed. The upstream checker
  limitation remains as described in `validation.md`.
- Offline wheel/source build: passed. Inspected built `Requires-Dist` metadata
  and its ONNX extra marker: affected representative versions through 1.21.0
  and version 2.0.0 were rejected; 1.22.0 and pinned 1.23.2 were accepted.
- The hashed dependency lock is unchanged and its ONNX pin satisfies the new
  metadata. No new third-party artifacts were installed for this correction.
- An initial run could not use the system pytest temporary directory; rerunning
  with a dedicated repository-local temporary directory passed.

ONNX 1.22.0 was checked as a metadata boundary, not executed locally. Physical
accelerators, mobile devices, and new PyTorch/ExecuTorch pairings were not tested.
Hosted checks for this correction are tracked on PR #3; local results do not
stand in for its cross-platform and native ExecuTorch jobs.
