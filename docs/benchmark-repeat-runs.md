# Screen repeat-run p95 stability

Run the same workload under controlled conditions, retain the separate
EdgeForge v1 reports, then run from this repository with Python 3.11 or newer:

```sh
python scripts/benchmark_repeat.py run-1.json run-2.json run-3.json
```

The tool reads 2–16 explicitly selected local reports, at most 256 KiB each,
without modifying them. It requires distinct timezone-qualified measurement
timestamps and checks that the reported bundle digest, runtime/version,
providers, benchmark options, thread/case counts, device descriptors,
EdgeForge version and timing scope match. A failed numerical agreement or a
difference between settings suppresses all latency aggregates.

| Result | Exit code |
| --- | ---: |
| Summary of report-level p95 minimum, median and maximum | 0 |
| Declared settings differ | 1 |
| Invalid or unavailable input; no summary | 2 |
| One or more reports failed numerical agreement | 3 |

Output does not include filenames, timestamps, device descriptors, or the
ordered per-run measurements. The extrema can still reveal individual
measurements and should not be shared when timings are sensitive. This is a
descriptive summary of each report's p95, not a pooled p95 or confidence
interval. Matching labels and distinct timestamps do not attest hardware or
prove separate executions. This tool does not fully validate report schemas.
Use the [evidence checklist](benchmark-evidence-checklist.md) for independent
verification and [the p95 budget check](benchmark-budgets.md) for one-run
threshold decisions.
