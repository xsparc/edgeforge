# EF-014 validation

Validated 2026-11-15.

Acceptance: `tests/test_bundle_identity_export.py`.

Full pytest: 145 passed, one optional native ExecuTorch test skipped. ONNX runtime tests passed. Ruff lint and format checks passed. Wheel and source distribution builds passed. Synthetic identity vector and exact export checks passed without inference.

Static and date-aware strict governance (`--as-of 2026-11-15 --strict`) passed.
Skipped optional checks are not passes. Hosted CI is assessed separately after push.
Python suites emitted an existing Starlette/httpx deprecation warning.
