# EF-010 validation

Validated 2026-11-10.

135 tests passed, one optional native ExecuTorch test skipped. Native ONNX Runtime CPU coverage and the executable portable example passed. Ruff lint and formatting passed. Existing Starlette/httpx deprecation remains; no physical-device or timing claims.

Acceptance: `tests/test_source_review.py`. Skipped optional checks are not passes. HTML layouts are unchanged.

Static governance and date-aware strict governance (`--as-of 2026-11-10 --strict`) passed.
Wheel and source distribution builds passed using installed dependencies; archive inventories exclude private state and environment directories.
