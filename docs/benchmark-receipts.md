# Local benchmark evidence receipts

When keeping a before/after report pair for later review, save a receipt at the
time you collect the reports. This standalone Python 3.11+ tool needs no runtime
installation, model loading, credentials, or network access.

From the repository root, in a POSIX shell or Command Prompt:

```sh
python scripts/benchmark_receipt.py --before before.json --after after.json --output receipt.json
python scripts/benchmark_receipt.py --before before.json --after after.json --verify receipt.json
```

Use a **new** receipt filename outside the repository. The tool refuses to
overwrite an existing file. Check the exit status, and retain the receipt
separately from the reports in storage controlled by the reviewer. Without
`--output` a new receipt goes to stdout. Prefer the explicit option to shell
redirection, which could truncate an input file before Python starts. The
verifier accepts canonical ASCII JSON with LF or CRLF as the final line ending.

Inputs are explicitly named, nonempty local regular files of at most 256 KiB
each; a receipt must fit within 1 KiB. The tool records the format version,
before/after roles, byte counts and SHA-256 digests, not filenames, contents or
machine identifiers. It compares exact bytes, so reformatting a report changes
the result. Exit codes: 0, generated or matched; 1, receipt and reports do not
match; 2, invalid invocation or unreadable, unsupported, empty or oversized input or a failed output write.

## Scope and privacy

A receipt does **not** parse reports, validate their schema, prove authorship,
establish execution, or decide whether a pair is comparable. It is unsigned; a
sender who can replace both the reports and the receipt can defeat the check.
Fingerprints and sizes can also correlate a report across reviewers, so keep
the receipt private unless you have a reason to share it. Use only explicit
local paths you control; this tool is not a sandbox for arbitrary paths.
Use the [benchmark review checklist](benchmark-evidence-checklist.md) for
independent source verification and interpreting results.
