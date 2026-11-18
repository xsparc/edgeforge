# EF-005 validation

Validated 2026-10-31 on the service-interoperability stack after merged EF-004.

- Full Python suite: 85 passed, one skipped (native ExecuTorch unavailable).
  The subsequent numeric/identity test brought the focused comparison suite to
  20 passing cases; all 19 earlier comparison cases were rerun with it.
- Twenty comparison tests cover real synthetic ONNX measurements, source bundle
  binding, compatible and changed warmup options, signed reverse direction,
  strict nested evidence, fixed ordered reasons and altered digests/deltas.
- JSON/CSV subprocess stdout matches exclusive-file output byte for byte.
  Hostile labels remain text-prefixed; oversized input and output collision
  leave retained evidence unchanged and return sanitized diagnostics.
- Ruff lint and format checks and public schema generation passed.

Tests make no timing pass/fail claim. Capability descriptors are synthetic to
avoid publishing machine data. Model execution is forbidden during offline
comparison. The full suite used normal local permissions for Windows asyncio
socket pairs. Existing Starlette/httpx deprecation remains. CI retains native
ExecuTorch Linux coverage; this local run does not claim to have executed it.

Static and 2026-10-31 strict project governance checks passed.
Offline source and wheel builds passed. Archive member inspection found no
private state directories.
