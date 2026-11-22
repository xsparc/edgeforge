# Reviewing retained benchmark evidence

This checklist is for reviewers who receive a comparison bundle or rendered
report rather than the original benchmark workspace. The commands below refer
to the implementation under review in
[PR #2](https://github.com/xsparc/edgeforge/pull/2), not to an installable
release from the default branch. Use the reviewed implementation; do not
install runtimes or execute models from a received evidence package.

## Record the evidence that was actually checked

All example filenames are synthetic. Use files retained independently of the
received bundle if the review needs to check more than internal consistency.

| Evidence available | Check | What success establishes |
| --- | --- | --- |
| Comparison bundle only | `edgeforge comparison-bundle-verify bundle.json` | The embedded reports and derived comparison agree. Both scope flags are false. |
| Independently retained before and after reports | `edgeforge comparison-bundle-verify bundle.json --before before.json --after after.json` | `source_checked` is true if both reports match their roles; `identity_checked` remains false. |
| Independently retained identity record | `edgeforge comparison-bundle-verify bundle.json --identity identity.json` | `identity_checked` is true on a match; it does not imply the source reports were checked. |
| Both independent forms of evidence | `edgeforge comparison-bundle-verify bundle.json --before before.json --after after.json --identity identity.json` | Both flags are true on a match. |
| Identity record only | `edgeforge comparison-bundle-identity-check identity.json` | The record is well formed. No bundle was read or verified. |

For HTML or CSV, use the
[export-verification workflow](https://github.com/xsparc/edgeforge/blob/71eaf00e92a35118372da63c46612121fb2edd24/docs/bundle-identity-verification.md)
with the appropriate bundle and evidence. Checking a rendered file against a
bundle does not substitute for checking that bundle against independent evidence.
Keep the exact export bytes rather than opening and resaving the file first.

If the check fails, record the failure separately. Do not retain a previous
success as evidence for different inputs or silently switch to a weaker check.
An identity bundled by the sender is not independent; a matching digest is not
a signature, and none of these checks establishes who ran a benchmark.

## Decide what may be compared or shared

- Retain the before/after roles and the verification scope beside a review
  decision. A matched pair can still be unsuitable for evaluating speed.
- Before comparing latency, check workload, warmup/iteration counts, timing
  boundaries, preprocessing, runtime versions and provider settings. Treat
  unsupported or unknown device conditions as unknown rather than equivalent.
  A reported provider is not proof of per-node accelerator placement.
- Report numerical agreement separately from latency. Agreement with golden
  vectors is not task accuracy. Process RSS is not GPU memory; pooled timings
  are not confidence intervals. See the
  [measurement notes](https://github.com/xsparc/edgeforge/blob/71eaf00e92a35118372da63c46612121fb2edd24/docs/benchmarking.md).
- Keep model files, test vectors, logs, private filenames and machine-specific
  identifiers out of public review. Check exported contents before publishing;
  a successful verification does not certify that those contents are safe to
  share. Do not edit checked bytes and then present them as the original export.

## Next steps suggested by this review

Improve the review path first: surface the actual verification scope in review
handoffs, and require a clear comparability decision before quoting timing deltas.

Two follow-on capabilities are worth scoping separately: **local threshold
reports** that distinguish an incomparable run from a failed latency budget,
and **independently retained evidence receipts** that bind report roles and an
explicit verification scope. A receipt would record digests and a contract
version, not collect machine or operator identity, and would not replace
source verification or signing. Neither capability is implemented by this
documentation change.
