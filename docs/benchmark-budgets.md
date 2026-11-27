# Local p95 benchmark budget

Use this offline Python 3.11+ check to screen one retained EdgeForge v1
benchmark report against a latency limit you choose:

```sh
python scripts/benchmark_budget.py --report report.json --max-p95-ms 12.5
```

The limit is positive and expressed in milliseconds. Equality passes. The
tool reads an explicitly selected local regular UTF-8 JSON file (up to 256 KiB)
and checks only the version, p95 latency and numerical agreement status. It
rejects duplicate JSON members and nonfinite numeric literals. It does not
change the report, load models, use network access, or include the input path,
measurements, or limit in output.

| Outcome | Exit code |
| --- | ---: |
| `within_budget` | 0 |
| `above_budget` | 1 |
| Invalid arguments or report; no outcome emitted | 2 |
| `agreement_failed`; latency result withheld | 3 |

Use the [benchmark review checklist](benchmark-evidence-checklist.md) to
verify report evidence independently. This is an absolute check on one
reported measurement, not full schema validation, authenticity verification,
a cross-device comparison, or proof that the limit will hold for another run.
Set budgets from a representative workload and controlled device conditions.
