import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_receipt.py"


class BenchmarkReceiptCLI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.before = root / "private-before.json"
        self.after = root / "private-after.json"
        self.receipt = root / "receipt.json"
        self.before.write_bytes(b'{"value":"private-marker-before"}\n')
        self.after.write_bytes(b'{"value":"private-marker-after"}\n')

    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, CLI, "--before", self.before, "--after", self.after, *extra],
            capture_output=True,
            check=False,
            timeout=5,
        )

    def test_receipt_is_deterministic_and_omits_names_and_contents(self):
        first = self.run_cli()
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, self.run_cli().stdout)
        self.assertEqual(first.stderr, b"")
        receipt = json.loads(first.stdout)
        self.assertEqual(set(receipt), {"schema_version", "before", "after"})
        self.assertEqual(receipt["schema_version"], 1)
        for role, report in (("before", self.before), ("after", self.after)):
            data = report.read_bytes()
            self.assertEqual(
                receipt[role],
                {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)},
            )
            self.assertNotIn(report.name.encode(), first.stdout)
            self.assertNotIn(b"private-marker", first.stdout)

    def test_verification_detects_swapped_roles_and_same_size_change(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        self.receipt.write_bytes(generated.stdout)
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 0)
        self.receipt.write_bytes(generated.stdout.rstrip(b"\r\n") + b"\r\n")
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 0)
        before, after = self.before.read_bytes(), self.after.read_bytes()
        self.before.write_bytes(after)
        self.after.write_bytes(before)
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 1)
        self.before.write_bytes(before)
        self.after.write_bytes(after.replace(b"marker", b"edited"))
        result = self.run_cli("--verify", self.receipt)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"private-marker", result.stderr)

    def test_explicit_output_never_overwrites_existing_files(self):
        result = self.run_cli("--output", self.receipt)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        saved = self.receipt.read_bytes()
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 0)
        self.assertEqual(self.run_cli("--output", self.receipt).returncode, 2)
        self.assertEqual(self.receipt.read_bytes(), saved)
        before = self.before.read_bytes()
        self.assertEqual(self.run_cli("--output", self.before).returncode, 2)
        self.assertEqual(self.before.read_bytes(), before)

    def test_noncanonical_and_oversized_receipt_fail(self):
        generated = self.run_cli()
        self.assertEqual(generated.returncode, 0)
        self.receipt.write_bytes(generated.stdout.rstrip() + b" \n")
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 1)
        self.receipt.write_bytes(b"x" * 1025)
        self.assertEqual(self.run_cli("--verify", self.receipt).returncode, 2)

    def test_size_limit_and_path_free_errors(self):
        for size, code in ((0, 2), (256 * 1024, 0), (256 * 1024 + 1, 2)):
            with self.subTest(size=size):
                self.before.write_bytes(b"x" * size)
                result = self.run_cli()
                self.assertEqual(result.returncode, code)
                if code:
                    self.assertEqual(result.stdout, b"")
                    self.assertNotIn(self.before.name.encode(), result.stderr)
        self.before.unlink()
        missing = self.run_cli()
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn(self.before.name.encode(), missing.stderr)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a POSIX FIFO")
    def test_special_file_rejected_without_blocking(self):
        self.before.unlink()
        os.mkfifo(self.before)
        self.assertEqual(self.run_cli().returncode, 2)


if __name__ == "__main__":
    unittest.main()
