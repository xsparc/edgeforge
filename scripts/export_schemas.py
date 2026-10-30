"""Export public transport contracts from the executable models."""

import json
from pathlib import Path

from edgeforge.benchmark import BenchmarkReport
from edgeforge.comparison import ReportComparison
from edgeforge.contracts import Manifest
from edgeforge.reports import ReportEvidence
from edgeforge.service import create_app


def main():
    root = Path(__file__).resolve().parents[1] / "schemas"
    root.mkdir(exist_ok=True)
    schemas = {
        "manifest.schema.json": Manifest.model_json_schema(),
        "report.schema.json": BenchmarkReport.model_json_schema(),
        "report-evidence.schema.json": ReportEvidence.model_json_schema(),
        "comparison.schema.json": ReportComparison.model_json_schema(),
        "openapi.json": create_app({}, "schema-generation-only-" + "x" * 32).openapi(),
    }
    for name, schema in schemas.items():
        (root / name).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", "utf-8")


if __name__ == "__main__":
    main()
