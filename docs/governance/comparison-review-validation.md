# EF-006 validation

Validated 2026-11-04 on the runtime-benchmarks stack after merged MVP PR #3.

- Full Python suite: 109 passed, one skipped (native ExecuTorch unavailable locally).
- New review suite: 23 passing cases for strict intake, top-level completeness,
  duplicate fields, malformed UTF-8, nesting, versions, nonfinite values,
  source replacement, direction and exact canonical CSV tampering.
- Native ONNX acceptance uses changed warmup options, source-bundle checks and
  deliberately failed retained agreement. Offline operations forbid model execution.
- Ruff lint and format checks passed.
- Chromium at 1280x900 and 390x900: no page overflow or script execution, escaped
  hostile label, visible failed agreement and incompatibility, three contained
  tables. Mobile screenshot inspected.

The existing Starlette/httpx warning remains. Full tests used normal local socket
permissions. No timing gate, new physical-device validation or measurement
attestation is claimed. Existing Linux CI retains native ExecuTorch coverage.

Project-specific static and 2026-11-04 strict governance checks passed.
Offline source/wheel builds passed; archive inspection found no private state.
The plugin self-checker was also attempted; it requires project identity
opensteward-control-plane and its own registry dialect, so it rejects these
independent project registries. The repository-specific gate is applicable here;
no project identity or historic registry was rewritten to satisfy that self-check.
