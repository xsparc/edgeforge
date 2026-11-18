# ADR 0013: Retained bundle identity

Status: accepted
Date: 2026-11-15

## Decision

```sh
edgeforge comparison-bundle-identity-schema
edgeforge comparison-bundle-identity bundle.json --output identity.json
edgeforge comparison-bundle-verify bundle.json --identity identity.json --before before.json --after after.json
edgeforge comparison-bundle-render bundle.json --identity identity.json --format html --output review.html
edgeforge comparison-bundle-verify-export bundle.json review.html --format html --identity identity.json
python examples/bundle_review.py review-demo
```

The closed version-1 identity record preserves existing identity field names and
encoding. Its reader rejects duplicate/unknown/missing fields, non-integer versions
and sizes, unsupported constants and anything except 64 lowercase hex digest
characters. Records are capped at 4096 bytes; normalized byte counts must be 1 to
1,052,672. The generated schema is checked in and compared with the model in tests.
The reader additionally enforces duplicate and raw-byte constraints that schema
validation alone cannot express. Existing normalized digest and golden vector are
unchanged; the encoding is project-specific, not RFC 8785/JCS.

--output validates the record before exclusive UTF-8 pretty JSON plus LF export;
stdout identity behavior is preserved when omitted. --identity checks both digest
and normalized byte count on verification, rendering and exact export verification.
It is mutually exclusive with --expected-sha256. Optional independent source checks
compose with either identity gate. All checks precede output creation, and invalid
input/collisions return exit 2 with sanitized errors. SDK identity models are
revalidated to reject mutation. Valid matching replacement evidence cannot bypass
independent original source checks. Identity is not attestation.

The new bundle_review example uses entirely synthetic failed-agreement reports,
requires a new destination directory and guards against inference throughout.
It exercises CLI bundle creation, identity export, both render formats, exact
verification, collisions, tampering and consistent replacement, and preserves
original inputs and exports. It requires no optional runtime execution.

## Alternatives and acceptance

Reuse strict readers and existing renderers/identity encodings instead of introducing parallel interpretations. Acceptance: `tests/test_bundle_identity_record.py`, `tests/test_bundle_identity_export.py`. Bounds, negative inputs, independent checks and byte preservation are covered. Runtime execution and authority changes are outside this slice.
