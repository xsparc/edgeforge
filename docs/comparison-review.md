# Check and review retained comparisons

```console
edgeforge comparison-check comparison.json
edgeforge comparison-verify before.json after.json comparison.json
edgeforge comparison-verify before.json after.json comparison.csv --format csv
edgeforge comparison-html comparison.json --output review.html
```

Create JSON/CSV with the existing report-compare command. Comparison intake and
HTML output are limited to 512 KiB; each explicit source report to 256 KiB.
Unknown/missing fields, duplicate JSON keys, invalid UTF-8, unsupported versions
and inconsistent digests/deltas are rejected.

JSON verification accepts alternate whitespace/property order but requires the
same normalized report content and direction. CSV requires exact quoted fields,
UTF-8 without BOM, CRLF, literal text: prefixes and the canonical ten metric rows.
Spreadsheet resaving or newline conversion can invalidate CSV. Verification never
rewrites evidence. Reverse source arguments or change a retained cell to observe
exit 2; successful checks exit 0 with fixed local-consistency summaries.

HTML is a human review artifact, not verifier input. It displays report/bundle
identities, compatibility reasons, failed golden-output agreement and signed
changes. Scroll metric tables horizontally on narrow screens. Output is exclusive
after validation, with escaped labels and script-free CSP. No model executes.

Standalone consistency cannot prove that retained reports are the originals:
both sources and comparison can be replaced consistently. Retain independent
sources and use comparison-verify when this matters. Even source verification
proves no authorship, measurement or performance improvement. Failed numerical
agreement remains valid evidence, not a pass verdict.

The native workflow in tests/test_comparison_review.py benchmarks the built-in
ONNX bundle, retains changed options, exercises both verifiers and renders a
deliberately failed-agreement report. It makes no timing-based assertion.
