import runpy
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
check = runpy.run_path(str(ROOT / "scripts/check_governance.py"))["check"]


def test_current_and_overdue_governance():
    assert check(ROOT, date(2026, 10, 28)) == []
    assert "review.overdue" in check(ROOT, date(2099, 1, 1))


@pytest.mark.parametrize(
    "before,after",
    [
        ('project = "edgeforge"', 'project = "another-project"'),
        ('status = "implemented"', 'status = "invented"'),
        ('"src/edgeforge/bundle.py"', '"../outside.py"'),
        ('"tests/test_bundles.py"', '"tests/missing.py"'),
    ],
)
def test_rejects_drift_under_optimized_python(tmp_path, before, after):
    for directory in ("docs", "src", "tests", "scripts", "schemas", "requirements", ".github"):
        shutil.copytree(ROOT / directory, tmp_path / directory)
    evidence = tmp_path / "docs/governance/project-evidence.toml"
    evidence.write_text(evidence.read_text("utf-8").replace(before, after), "utf-8")
    result = subprocess.run(
        [sys.executable, "-O", "scripts/check_governance.py", "--strict"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert '"status": "fail"' in result.stdout
