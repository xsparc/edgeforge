# Maintenance review: deployment evidence and device coverage

This is a proposal, not a release or a statement that the proposed checks are
implemented. The default branch contains the project introduction. The portable
bundle contract and CLI are in [PR #1](https://github.com/xsparc/edgeforge/pull/1);
the native benchmark and subsequent evidence work build on that in
[PR #2](https://github.com/xsparc/edgeforge/pull/2). Keep the implementation
stack and its review order intact.

## Improve

1. **Make verification responses safe to consume programmatically.** The
   [verification scope notes](https://github.com/xsparc/edgeforge/blob/71eaf00e92a35118372da63c46612121fb2edd24/docs/bundle-verification-scope.md)
   distinguish a parsed identity record from a source-checked or identity-checked
   bundle. Prioritize the already-planned response contract (EF-017): a versioned
   schema, a closed reader, and parity tests against the CLI's success output.
   Test unsupported versions, contradictory scope and no success record after a
   failed check. Reading a response validates its shape, not the checks it claims.
2. **Make published benchmark evidence privacy-safe by construction.** The
   [security notes](https://github.com/xsparc/edgeforge/blob/71eaf00e92a35118372da63c46612121fb2edd24/docs/security.md)
   already say reports omit host identifiers and local paths. Put that promise
   under regression test across supported shareable output formats. Use synthetic
   markers in the working directory, environment and runtime error detail;
   assert they do not appear in public outputs and that allowed runtime/version
   information and fixed error categories still do. Keep evidence local unless
   someone explicitly exports it.

## Expand

1. **Add a repeatable physical-device benchmark profile.** Start with one target
   and the existing synthetic workload, not a new scheduler. Capture allowlisted
   device class, power mode, coarse thermal state, runtime and provider, plus
   warmup and iteration settings. Report latency, agreement and energy per
   inference only when a calibrated counter or meter provides usable readings.
   Mark unknown measurements as unavailable and separate measured placement
   from a provider's declared availability. Exclude serial numbers, hostnames
   and free-form environment dumps. Compare results only for like workloads and
   settings.
2. **Add offline bundle signature verification.** Extend the existing hash
   integrity model with a detached signature tied to a bundle digest and a public
   key supplied through a separate trusted channel. Prove the verifier rejects
   changed bytes and untrusted signing keys without loading a model or using the
   network. Keep signing keys outside the repository and runtime. A matching
   signature establishes that a trusted key signed the bytes, not that the model
   is safe to execute or that its benchmark claims are true.

## Sequence and guardrails

Review PR #1 before PR #2. On the implementation stack, specify the response
contract first, then add export privacy regressions before collecting or sharing
physical-device evidence. Keep the first device trial synthetic and local.
Signature verification is a separate capability; it must not weaken the
trusted-model boundary or introduce automatic downloads or execution.
