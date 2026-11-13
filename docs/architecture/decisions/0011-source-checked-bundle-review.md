# ADR 0011: Source checked bundle review

Status: accepted
Date: 2026-11-13

## Decision


```sh
edgeforge comparison-bundle-verify bundle.json --before before.json --after after.json
edgeforge comparison-bundle-render bundle.json --format html --before before.json --after after.json --output review.html
edgeforge comparison-bundle-render bundle.json --format csv --output review.csv
```

Both commands accept optional paired --before/--after reports. A partial pair,
reversal or mismatch fails; a self-consistent replacement bundle cannot bypass
independent source checks. Without source options, standalone verification remains
compatible. SDK verify_sources returns the validated bundle after comparing it
with a recomputed bundle from the explicit reports.

Rendering defaults to HTML and reuses the exact existing comparison HTML/CSV
renderers. Validation and optional source checks precede exclusive output creation.
Reports remain capped at 256 KiB each, retained bundles at 1,052,672 bytes and
rendered output at 512 KiB. SDK render_bundle revalidates mutable nested models,
rejects unsupported formats and applies the output cap. Failed-agreement evidence
remains valid descriptive input.

Verification is read-only; exports never overwrite existing files. Success
verification returns fixed JSON and exit 0; invalid input, mismatch or collision
uses fixed error categories and exit 2. No inference or browser execution occurs.
Independent sources prove local consistency, not provenance or device performance.
A matching bundle alone cannot detect consistent substitution.

## Alternatives and acceptance

Reuse existing validators and exact renderers. Exclusive creation avoids replacing retained evidence. Acceptance covers independent source checks, replacement evidence, collisions, bounds, byte preservation and non-execution. No runtime authority or renderer-layout changes.
