# DirectionBriefV1: Runtime dependency maintenance

- schema_version: 1
- baseline_commit: 8218d433c875a96274c68bb04753a828ca0c2a19
- scanned_at: 2026-11-02
- coverage: MVP PR state and CI, package constraints and lock, runtime release
  notes, recent ONNX advisories, architecture and existing growth proposal.

## ONNX minimum

Finding: the declared `onnx>=1.17,<2` range admits versions affected by four
ONNX advisories, although the checked-in 1.23.2 lock is already patched.
The advisories identify 1.22.0 as the first patched version:
[ConvTranspose inference](https://github.com/advisories/GHSA-6pwm-x34p-fvj2),
[packed sub-byte expansion](https://github.com/advisories/GHSA-q69g-f4f5-v8m7),
[Scan inference](https://github.com/advisories/GHSA-m4pr-6v3c-6fgr), and
[RNN/GRU/LSTM inference](https://github.com/advisories/GHSA-48m4-24cq-37qf).

- source_event_date: 2026-10-28, GitHub Advisory Database publication; fixes
  shipped earlier in 1.22.0.
- confidence: high; verified affected ranges against the GitHub advisory API.
- relevance: optional ONNX model validation and quantization dependency.
- direction_alignment: preserve existing runtime adapters and trusted inputs.
- opportunity_or_risk: constrained downstream environments can satisfy the old
  metadata with an affected ONNX version; no exploitation is claimed.
- engineering_cost: low; dependency metadata and validation evidence only.
- disposition: adopt, within authorized corrections to the existing MVP PRs.
- roadmap_delta: none; correction belongs to EF-003 integration.
- verification_needed: built metadata excludes affected versions, retains the
  pinned dependency, and existing runtime and integration checks pass.

## Runtime releases

Finding: the locked ONNX Runtime 1.31.1 and selected ExecuTorch 1.5.1 remain the
latest stable releases reported by their official release APIs. The ONNX Runtime
patch fixes an OpenVINO/Python build regression; ExecuTorch's release includes
expanded delegate packaging and Arm support.
[ONNX Runtime](https://github.com/microsoft/onnxruntime/releases/tag/v1.31.1),
[ExecuTorch](https://github.com/pytorch/executorch/releases/tag/v1.5.1).

- source_event_date: 2026-10-26 and 2026-09-23 respectively.
- confidence: high for release metadata; target-device coverage remains absent.
- relevance: supported adapters and future portability work.
- direction_alignment: continue using upstream runtimes.
- opportunity_or_risk: new upstream capabilities do not prove EdgeForge support.
- engineering_cost: none for the present correction.
- disposition: no-change.
- roadmap_delta: none.
- verification_needed: physical-device and delegate tests before support claims.

## PyTorch release boundary

Finding: PyTorch 2.15.0 is available. Its security notes describe checkpoint
loading and shared-memory-manager fixes. EdgeForge uses trusted exported PTE
programs and does not load pickle checkpoints. The current compatibility range
remains 2.14 with ExecuTorch 1.5.1; this scan does not establish that upgrading
that pair is compatible or that every PyTorch security issue is unreachable.
[PyTorch 2.15.0](https://github.com/pytorch/pytorch/releases/tag/v2.15.0).
PyTorch 2.14.1 also fixes MPS linear-algebra and CUDA binary issues; neither
backend is validated by the current CPU-only ExecuTorch CI.
[PyTorch 2.14.1](https://github.com/pytorch/pytorch/releases/tag/v2.14.1).

- source_event_date: 2026-10-28 and 2026-09-30 respectively.
- confidence: high for release notes; limited for untested execution paths.
- relevance: optional export/runtime dependency and future device validation.
- direction_alignment: validate a compatible runtime pair before expanding it.
- opportunity_or_risk: runtime upgrades can alter exported-program compatibility.
- engineering_cost: medium for a separate compatibility validation slice.
- disposition: monitor.
- roadmap_delta: none; advisory only, no upgrade authorized by this finding.
- verification_needed: upstream compatibility evidence and native export/load
  checks on the candidate pair before changing supported versions.

## Recommendation and gaps

Correct the ONNX minimum in existing PR #3 without changing the hashed lock or
runtime behavior. Preserve the already proposed EF-006 acceptance criteria in
`docs/next-milestone.md`; it remains planned and needs separate authorization.
This scan is not a complete transitive dependency audit. Native model parsing
remains outside a sandbox. Physical devices, accelerator delegates, and the
PyTorch 2.15/ExecuTorch pairing remain unvalidated. Local native ExecuTorch and
hosted platform checks are reported separately in correction evidence.
