# EF-015 validation

Validated 2026-11-15.

Acceptance: `tests/test_bundle_identity_record.py`, `tests/test_bundle_identity_export.py`.

Full pytest: 149 passed, one optional native ExecuTorch test skipped. ONNX checks passed. Ruff lint and formatting passed. Wheel and source-distribution builds passed. The new entirely synthetic bundle workflow passed under its no-inference guard; the existing golden vector is unchanged.

Static and date-aware strict governance (`--as-of 2026-11-15 --strict`) passed.
Skipped optional checks are not passes. Hosted CI is assessed separately after push.
An existing Starlette/httpx deprecation warning remains.
