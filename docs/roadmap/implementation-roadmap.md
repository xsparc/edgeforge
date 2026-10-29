# Implementation roadmap

The initial MVP is delivered in three stacked PRs. Merge approval is separate.

| Slice | Scope | Acceptance |
| --- | --- | --- |
| EF-001 | Contracts, bundles, CLI, architecture, governance | Identical bundle bytes; strict tensor validation; corruption and unsafe archive rejection; inspect and schema commands |
| EF-002 | Runtime adapters, preprocessing, quantization, benchmarks | Real ONNX inference and quantization; ExecuTorch adapter contract and Linux integration; latency, RSS, size and output agreement reports; runtime errors remain explicit |
| EF-003 | Service interoperability, examples, CI, documentation | Authenticated registered-bundle API; bounded worker concurrency; API tests; installable package and runnable example; platform CI and accurate limitations |

## Next decisions

Physical-device validation, static calibration, richer preprocessing, signed
artifact provenance, external weight files, and distributed worker scheduling
require separate bounded work. Reconsider after MVP review and real-device
feedback. No performance improvement is assumed from quantization alone.

Ongoing stewardship reviews upstream runtime changes, CI failures, dependency
compatibility, user feedback, and evidence freshness. It proposes the next
bounded slice and preserves review gates for merges, releases, and deployments.

## EF-004: Retained benchmark report review

Initialize five report-review tasks: strict intake, reader schema, retained bundle verification, portable CSV and native workflow acceptance. Preserve the benchmark producer/API contract.

Decision: docs/architecture/decisions/0002-retained-report-review.md.
Acceptance: Strict report schema and arithmetic; bounded read-only checks; bundle/configuration/count matching; safe CSV and real synthetic ONNX workflow.
Next iteration: docs/next-milestone.md (planned only).
