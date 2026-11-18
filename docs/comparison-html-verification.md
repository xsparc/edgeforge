# Retained comparison HTML verification

```sh
edgeforge comparison-verify-html comparison.json before.json after.json review.html --identity identity.json
```

The command validates the retained comparison, recomputes it from explicit reports,
checks the optional identity record and compares exact UTF-8 HTML bytes with the
existing renderer. Both report sources are required. A matching replacement
identity cannot bypass a source mismatch. SDK `verify_comparison_html` verifies
rendered bytes against a validated comparison; callers supply independent sources
through the CLI or existing `verify_comparison` separately.

Comparison and HTML intake are capped at 512 KiB; existing report and identity
limits remain unchanged. Markup, CSP, style, encoding and newline changes fail
without repair. Success emits fixed JSON with verified true and exit 0; errors
use existing fixed categories and exit 2. Verification never writes inputs,
opens a browser or runs inference. Existing rendering formats remain unchanged.

Exact verification is renderer-version-sensitive. It is not a signature, browser
safety certification, provenance claim or proof of equivalent device performance.
Failed-agreement reports remain valid descriptive evidence. Retain independent
sources and identity targets to detect substitution.
