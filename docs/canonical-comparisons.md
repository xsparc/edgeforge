# Canonical comparisons

The `edgeforge-comparison-json-v1` profile encodes a fully revalidated comparison model using Python JSON: sorted keys, compact separators, ASCII escaping, no nonfinite numbers, UTF-8 and exactly one terminal LF. The LF participates in SHA-256. Model normalization occurs first; Python float spelling, including negative zero, is preserved. This profile is not RFC 8785/JCS and makes no cross-language number serialization promise. Any future byte-rule change requires a new profile.

```sh
edgeforge comparison-identity comparison.json
edgeforge comparison-canonical comparison.json --output canonical.json
edgeforge comparison-check comparison.json --expected-sha256 EXPECTED_DIGEST
edgeforge comparison-html comparison.json --output review.html --expected-sha256 EXPECTED_DIGEST
```

Canonical export also accepts `--expected-sha256`. Expected values must be exactly 64 lowercase hexadecimal characters and are checked before output creation. The identity summary contains schema_version, canonicalization, comparison_sha256, bytes and interpretation=retained_identity_not_attestation. Export uses exclusive creation and returns the identity only after a successful write. Intake and canonical output are bounded to 512 KiB. SDK objects are revalidated, including nested mutations.

The canonical digest differs from an original file-byte digest and from each embedded source-report digest. Equivalent whitespace/key order normalize identically; reversed direction or consistent content replacement changes identity. Failed agreement remains descriptive evidence, not an export failure. Retain the expected digest independently. A digest establishes neither authorship nor signature, trustworthy measurements, runtime compatibility or source agreement; use comparison-verify separately against explicit reports. No timing threshold or new inference run is introduced by retention commands.
