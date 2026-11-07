# Offline benchmark report review

```console
edgeforge report-check report.json
edgeforge report-check report.json --bundle model.efb
edgeforge report-schema
edgeforge report-csv report.json --output report.csv
```

The report reader checks the existing version-1 benchmark format, finite numbers,
closed nested fields, timestamp timezone, nonnegative ordered latency summaries,
RSS arithmetic, output-agreement counts/fractions and invocation budget. It
accepts a failed agreement result as a valid report; report-check exits 0 when
validation succeeds, not when model accuracy is established. Invalid input or
I/O exits 2 with fixed JSON diagnostics and no input content or paths.

With --bundle it also checks bundle identity, runtime configuration, sizes, case
count and compared element count. This reads and validates the bounded bundle
without native model execution. It cannot verify a latency measurement, actual
runtime/provider behavior or report authorship. No signature is implied.

Report JSON is limited to 256 KiB. CSV has a single data row, quoted cells,
text-prefixed labels and UTF-8/CRLF. Output creation is exclusive. Input files
are unchanged. The CSV includes scoped latency, sampled whole-process RSS,
artifact sizes and golden-output agreement. It does not claim VRAM use,
task-level accuracy, or performance on another device. The strict schema is
also checked in as schemas/report-evidence.schema.json; the producer's original
schema remains available for existing integrations.
