import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_budget.py"


class BenchmarkBudgetCLI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.report = Path(temp.name) / "private-report.json"
        self.write_report(0.125)

    def write_report(self, p95, *, passed=True, version=1):
        self.report.write_text(
            json.dumps(
                {
                    "schema_version": version,
                    "latency_ms": {"p95": p95},
                    "agreement": {"passed": passed},
                    "note": "private-record-marker",
                }
            ),
            encoding="utf-8",
        )

    def run_cli(self, *extra, limit="0.125"):
        return subprocess.run(
            [sys.executable, CLI, "--report", self.report, "--max-p95-ms", limit, *extra],
            check=False,
            capture_output=True,
            timeout=5,
        )

    def assert_outcome(self, expected_code, expected_outcome):
        result = self.run_cli()
        self.assertEqual(result.returncode, expected_code)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(
            json.loads(result.stdout),
            {"outcome": expected_outcome, "schema_version": 1},
        )

    def test_inclusive_boundary_and_above_budget(self):
        self.assert_outcome(0, "within_budget")
        self.report.write_text(
            '{"schema_version":1,"latency_ms":{"p95":0.1250000000000000000000001},'
            '"agreement":{"passed":true}}',
            encoding="utf-8",
        )
        self.assert_outcome(1, "above_budget")

    def test_failed_agreement_outweighs_latency(self):
        for p95 in (0.01, 5):
            with self.subTest(p95=p95):
                self.write_report(p95, passed=False)
                self.assert_outcome(3, "agreement_failed")

    def test_wrong_types_and_versions_never_emit_a_decision(self):
        for p95, passed, version in (
            (True, True, 1),
            ("0.1", True, 1),
            (-0.1, True, 1),
            (float("inf"), True, 1),
            (0.1, "false", 1),
            (0.1, True, True),
            (0.1, True, 2),
        ):
            with self.subTest(p95=p95, passed=passed, version=version):
                self.write_report(p95, passed=passed, version=version)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertNotIn(b"private-", result.stderr)

    def test_duplicate_keys_and_oversized_reports_fail(self):
        for data in (
            b'{"schema_version":1,"latency_ms":{"p95":1,"p95":0},"agreement":{"passed":true}}',
            b" " * (256 * 1024 + 1),
        ):
            self.report.write_bytes(data)
            result = self.run_cli()
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b"")

    def test_invalid_limit_and_invocation_dont_echo_arguments(self):
        for limit in ("NaN", "0", "-1", "private-limit"):
            result = self.run_cli(limit=limit)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b"private-", result.stderr)
        result = self.run_cli("private-unexpected-argument")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b"private-", result.stderr)

    def test_unavailable_file_does_not_echo_path(self):
        self.report.unlink()
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b"private-", result.stderr)
