# EF-007 validation

Validated 2026-11-05.

116 tests passed, one optional native ExecuTorch test skipped. ONNX Runtime CPU tests passed. Ruff lint and formatting passed; wheel and source distribution built offline.

Acceptance: `tests/test_comparison_identity.py` covers the new retained-evidence contract. Existing suites cover strict intake and source consistency. No timing assertions or new attestation claims.

Existing Starlette/httpx deprecation remains; optional runtime/service skips are not passes.

Project-specific static and 2026-11-05 strict governance checks passed. Diff whitespace and public-file privacy scans passed. Offline wheel/source builds passed; archive inspection found no private state.
