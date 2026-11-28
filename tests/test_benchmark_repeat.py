import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_repeat.py"


class RepeatBenchmarkCLI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def report(self, index, p95, **changes):
        path = self.root / f"private-report-{index}.json"
        report = {
            "schema_version": 1,
            "bundle_sha256": "a" * 64,
            "edgeforge_version": "0.1.0",
            "runtime": "onnx",
            "runtime_version": "example-1",
            "requested_provider": "CPUExecutionProvider",
            "active_providers": ["CPUExecutionProvider"],
            "options": {"warmup": 5, "iterations": 50, "atol": 1e-5, "rtol": 1e-4},
            "measurement_scope": "adapter",
            "cases": 2,
            "threads": 1,
            "device": {"descriptor": "private-device-marker"},
            "measured_at": f"2026-01-01T00:00:{index:02}+00:00",
            "latency_ms": {"p95": p95},
            "agreement": {"passed": True},
            **changes,
        }
        path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def run_cli(self, *paths):
        return subprocess.run(
            [sys.executable, CLI, *paths], check=False, capture_output=True, timeout=5
        )

    def test_summarizes_only_the_aggregate_and_keeps_evidence_unchanged(self):
        paths = [self.report(1, 9), self.report(2, 1), self.report(3, 5), self.report(4, 3)]
        original = [p.read_bytes() for p in paths]
        result = self.run_cli(*paths)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "schema_version": 1,
                "outcome": "summarized",
                "report_count": 4,
                "report_p95_ms": {"min": 1, "median": 4, "max": 9},
            },
        )
        self.assertNotIn(b"private-", result.stdout)
        self.assertEqual(result.stdout, self.run_cli(*reversed(paths)).stdout)
        self.assertEqual([p.read_bytes() for p in paths], original)

    def test_different_conditions_and_failed_agreement_never_emit_metrics(self):
        first = self.report(1, 1)
        for changes, code, outcome in (
            ({"cases": 3}, 1, "incomparable"),
            ({"device": {"descriptor": "other-private-device"}}, 1, "incomparable"),
            ({"agreement": {"passed": False}}, 3, "agreement_failed"),
        ):
            with self.subTest(changes=changes):
                result = self.run_cli(first, self.report(2, 2, **changes))
                self.assertEqual(result.returncode, code)
                self.assertEqual(
                    json.loads(result.stdout),
                    {"schema_version": 1, "outcome": outcome, "report_count": 2},
                )

    def test_same_timestamp_is_rejected_even_after_paths_and_offsets_change(self):
        first = self.report(1, 1)
        second = self.report(2, 2, measured_at="2026-01-01T08:00:01+08:00")
        self.assertEqual(self.run_cli(first, second).returncode, 2)

    def test_invalid_report_and_arguments_leave_private_values_out_of_errors(self):
        path = self.report(1, 1)
        other = self.report(2, True)
        for args in ((path, other), (path,), ("--private-argument",), (path,) * 17):
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"private-", result.stderr)

    def test_duplicate_properties_and_oversized_inputs_are_rejected(self):
        first = self.report(1, 1)
        second = self.report(2, 1)
        for content in (
            b'{"schema_version": 1, "schema_version": 1}',
            b" " * (256 * 1024 + 1),
        ):
            second.write_bytes(content)
            result = self.run_cli(first, second)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")
