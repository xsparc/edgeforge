# EF-016 validation

Validation date: 2026-11-18.
Acceptance: `tests/test_verification_scope.py`, `tests/test_bundle_identity_record.py`.

Full pytest: 150 passed, one optional native ExecuTorch test skipped. ONNX checks passed. Ruff lint/format and wheel/source-distribution builds passed. Standalone identity validation and every source/identity verification combination passed, including the synthetic portable workflow.

Static and date-aware strict governance (`--as-of 2026-11-18 --strict`) passed.
Skipped checks are not passes. Hosted CI is assessed separately after push.
An existing Starlette/httpx deprecation warning remains.
