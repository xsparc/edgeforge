# ADR 0006: Retained identities

Status: accepted
Date: 2026-11-07

## Decision

`ComparisonIdentity` is the closed version-1 contract for the existing canonical comparison identity summary. All five fields are required: integer schema_version=1, canonicalization=edgeforge-comparison-json-v1, a 64-character lowercase hexadecimal comparison_sha256, integer bytes from 1 through 524288, and interpretation=retained_identity_not_attestation. No defaults silently repair incomplete records.

```sh
edgeforge comparison-identity-schema
edgeforge comparison-identity comparison.json > identity.json
edgeforge comparison-verify-identity comparison.json identity.json
edgeforge comparison-check comparison.json --identity identity.json
edgeforge comparison-html comparison.json --identity identity.json --output review.html
edgeforge comparison-canonical comparison.json --identity identity.json --output canonical.json
```

Retained identity intake is bounded to 4096 bytes before parsing and rejects duplicate keys, malformed UTF-8/JSON, nonfinite values, deep nesting, unknown/missing fields and type coercion. The checked-in schema matches the executable model. SDK `read_identity` and `verify_identity_record` revalidate caller-owned models; verification compares both canonical byte count and digest. Equivalent JSON formatting of either record does not change the comparison target.

The optional `--identity` gate and `--expected-sha256` are mutually exclusive on check, HTML and canonical commands. Verification runs before output creation and preserves existing files. Standalone verification emits the existing fixed local-consistency summary; invalid evidence returns 2 with fixed diagnostics. Identity generation preserves its existing JSON fields and encoding profile.

The acceptance example in `tests/test_retained_identity.py` uses a generated ONNX model with synthetic device labels, retains its comparison identity, and exercises canonical/HTML review with no further inference. A deliberately failed-agreement report remains valid descriptive evidence. Consistent comparison replacement, reversed direction and byte-count tampering fail against the independently retained record; no timing threshold is used.

An identity record is not a signature, independent source proof or measurement attestation. Keep it independently. Use `comparison-verify` against explicit before/after reports for source consistency. Shell redirection is shell-managed and can overwrite a destination; the canonical/HTML output commands themselves create files exclusively.

## Alternatives and acceptance

Reuse the existing normalized exporters and semantic validators rather than trusting
self-reported fields or changing established byte profiles. Raw file-byte hashes
cannot substitute for normalized identity. Strict structural decoding precedes
semantic checks. Validation covers successful round trips, equivalent formatting,
whole-record replacement, direction, malformed/oversized evidence, SDK mutations
where applicable, fixed diagnostics and failure before any output write.

No runtime capability, simulator behavior, source admission, signing or deployment
change is included. The saved conversation-approved milestone defines this scope.
