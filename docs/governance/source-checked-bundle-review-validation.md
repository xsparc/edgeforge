# EF-013 validation

Validation date: 2026-11-13.
Acceptance: `tests/test_bundle_review.py`.

142 tests passed, one optional native ExecuTorch test skipped. Native ONNX CPU regression coverage passed; new bundle review gates use synthetic reports. Ruff lint and formatting passed.

Static and date-aware strict governance (`--as-of 2026-11-13 --strict`) passed.

Wheel and sdist builds passed; archive inventories exclude private state and environments. Existing Starlette/httpx deprecation remains. Skips are not passes.

HTML layouts remain unchanged. No browser execution, deployment or physical-device performance claims.
