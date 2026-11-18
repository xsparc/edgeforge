# ADR 0012: Bundle identity verification

Status: accepted
Date: 2026-11-15

## Decision

```sh
edgeforge comparison-bundle-identity bundle.json
edgeforge comparison-bundle-verify bundle.json --expected-sha256 DIGEST
edgeforge comparison-bundle-render bundle.json --format csv --expected-sha256 DIGEST --output review.csv
edgeforge comparison-bundle-verify-export bundle.json review.csv --format csv --before before.json --after after.json --expected-sha256 DIGEST
```

Identity encoding edgeforge-comparison-bundle-json-v1 validates the model, then
hashes its sorted-key compact JSON, UTF-8 without ASCII escaping, finite numbers
only, with a trailing LF. This is a project encoding, not RFC 8785/JCS. SHA-256 and
byte count describe these normalized bytes, not the original file or authorship.
A synthetic failed-agreement fixture pins digest
73e8de939468e4be371d6c9cfc42ccbbf7dc7747f1e789e5f9f8fb6e9b71cadc and 6072 bytes.

Verification and rendering accept an optional exactly 64-character lowercase hex
digest and paired independent sources. Gates run before exclusive output creation.
Exact export verification requires --format html or csv and compares all retained
bytes with the existing renderer. The export read is bounded at 512 KiB; bundles
retain their 1,052,672-byte bound and source reports their 256 KiB bound. Whitespace,
CSP and markup edits fail. Verification never writes or performs inference. Matching
replacement evidence can pass standalone verification; independent original sources
or an independently retained digest are necessary to detect substitution. Errors
return exit 2 with sanitized categories; success verification returns fixed JSON.

## Alternatives and acceptance

Reuse strict validators and existing serializers instead of introducing a second interpretation of retained evidence. Exclusive output avoids replacing prior evidence. Acceptance is in `tests/test_bundle_identity_export.py`. Bounds, malformed input, replacement and byte preservation are covered; runtime execution remains outside these review commands.
