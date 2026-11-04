# EF-004 validation

Validated 2026-10-29 against the EF-003 service implementation branch.

- Full Python suite: 66 passed, one skipped.
- Focused retained-report suite: 19 passed.
- Ruff lint/format and static/current-date strict governance: passed.
- Strict reader schema export and unchanged producer schema checks: passed.
- Offline source/wheel builds and installed CLI smoke: passed.
- Package archive inspection found no private state directories.

The new native ONNX workflow benchmarks the built-in synthetic model, validates
its report, checks retained bundle identity/configuration/counts without native
execution, and round-trips CSV via the installed CLI. It replaces capability
metadata with synthetic labels. Negative cases cover versions, digests, latency
order, RSS arithmetic, fractions, verdicts, unexpected fields, private fields,
nonfinite values, wrong source metadata, byte limits and non-overwrite.
Failed golden-output agreement remains valid report evidence.

Native ExecuTorch was unavailable locally and its existing test skipped; its
mocked adapter contract passed. The existing Starlette/httpx deprecation warning
remains. HTTP tests initially stalled in the sandbox's Windows asyncio socket
pair setup; the complete suite passed with normal local access. Package install
used project-local temporary files. No external service or device was deployed.
No physical accelerator, mobile target, signature or independent measurement
attestation is claimed.
