# ADR 0007: Source checked review

Status: accepted
Date: 2026-11-09

## Decision

A single review command composes the existing bounded comparison reader, explicit-source verifier and optional retained identity-file check before exporting HTML.

```sh
edgeforge comparison-review comparison.json before.json after.json --output review.html
edgeforge comparison-review comparison.json before.json after.json --identity identity.json --output checked.html
```

Both source reports are required. The command recomputes the comparison in before-to-after order and requires the retained comparison to match. If supplied, the independent identity record must also match its canonical digest and byte count. A matching identity does not bypass source verification: consistently replacing the comparison and identity still fails against different explicit source reports.

Each report and comparison uses its existing bounded reader; identity files are capped at 4096 bytes and HTML at the existing 512 KiB comparison limit. All checks finish before exclusive output creation. Invalid, missing, oversized, reversed or mismatched evidence returns 2 with a fixed diagnostic. Success returns 0; existing files and all inputs are preserved. The existing script-free escaped renderer and CSP are reused without changing layout.

The native synthetic acceptance workflow includes deliberately failed agreement, hostile markup, wrong sources with a matching identity, consistent replacement, reverse direction, malformed identity and oversized source data. Review does not invoke a runtime or impose timing thresholds. Source consistency and retained identity do not authenticate authorship, prove genuine measurements or establish device portability.

## Alternatives and acceptance

Compose existing semantic validators rather than trusting duplicated summaries or
using an identity as a substitute for source verification. Reuse existing byte
profiles. Render only after verification; reject malformed evidence instead of
repairing it. Acceptance covers correct and reversed sources, consistent
replacement, bounds, strict fields, no execution and exclusive output. Browser
checks apply to the new ToolCapsule layout; existing Python layouts are unchanged.
