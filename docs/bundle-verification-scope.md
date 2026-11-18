# Bundle verification scope

```sh
edgeforge comparison-bundle-identity-check identity.json
edgeforge comparison-bundle-verify bundle.json --identity identity.json --before before.json --after after.json
python examples/bundle_review.py review-demo
```

Standalone identity checking uses the existing closed reader and a 4096-byte bound.
It never reads a bundle or runs inference. Success is fixed JSON with schema_version
1, valid true and interpretation identity_record_validity_only. Malformed records,
duplicates and oversized input fail without modifying bytes. The synthetic bundle
workflow exercises a valid identity and a separate invalid duplicate-field record.

Successful comparison-bundle-verify and comparison-bundle-verify-export responses
now add source_checked and identity_checked booleans. They are true only when the
corresponding supplied sources or digest/identity file matched. A matching identity
alone does not imply an independent source check. Errors retain fixed categories
and no success output. The existing interpretation, schema_version and verified
fields remain; no retained bundle or rendered byte format changes. A consistent
replacement with its matching identity cannot bypass original source reports.
