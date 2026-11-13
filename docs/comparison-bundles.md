# Portable comparison bundles

```sh
edgeforge comparison-bundle-schema
edgeforge comparison-bundle before.json after.json --output comparison-bundle.json
edgeforge comparison-bundle-verify comparison-bundle.json
```

A version-1 envelope retains before and after report evidence, their derived
comparison and the fixed interpretation local_source_consistency_only. Every
outer field is required; unknown fields and duplicate JSON keys are rejected.
Strict existing report/comparison validators check components and the comparison
is recomputed from retained reports on every intake. Unsupported versions,
booleans/floats in the version field, non-finite JSON, excessive nesting, malformed
UTF-8 and inconsistent evidence fail. Failed numerical agreement is valid evidence.

Each normalized report is capped at 256 KiB, comparison at 512 KiB and the entire
input/output at 1,052,672 bytes (1 MiB plus 4096 envelope allowance). Export uses
compact sorted-key UTF-8 JSON with a terminal LF and exclusive output creation.
Verification reads bounded input and never rewrites it; formatting changes may
pass semantic verification. SDK create_bundle and encode_bundle revalidate models.
The checked-in JSON Schema describes structure; recomputation and byte bounds
remain runtime checks, not guarantees made by a schema validator alone.

Success verification prints fixed JSON and exits 0; malformed input, mismatch or
output collision uses existing fixed diagnostics and exits 2. No inference is
performed. A consistent replacement of both reports and comparison passes
standalone verification; independent source/identity verification is a subsequent
milestone. This envelope is not a signature, attestation or performance verdict.
