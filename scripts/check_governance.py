"""Validate EdgeForge's derived traceability index without external dependencies."""

import argparse
import json
import re
import tomllib
from datetime import date
from pathlib import Path, PurePosixPath


def check(root: Path, as_of: date | None = None) -> list[str]:
    errors = []
    try:
        data = tomllib.loads((root / "docs/governance/project-evidence.toml").read_text("utf-8"))
        assert data["schema_version"] == 1 and data["project"] == "edgeforge"
        assert data["authority"]["dhf_is_authoritative"] is False
        reviewed = date.fromisoformat(data["review"]["last_reviewed"])
        due = date.fromisoformat(data["review"]["review_due"])
        assert reviewed <= due
        if as_of and as_of > due:
            errors.append("review.overdue")
        objectives = {r["id"] for r in data["objectives"]}
        requirements = {r["id"] for r in data["requirements"]}
        seen = set()
        design_refs = set()
        for kind in ("objectives", "requirements", "work_items", "research_decisions"):
            for record in data[kind]:
                identity = record["id"]
                assert re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", identity)
                assert identity not in seen
                seen.add(identity)
                if kind == "requirements":
                    assert set(record["objective_ids"]) <= objectives
                    assert record["status"] in {"planned", "implemented", "deferred", "retired"}
                    fields = ["roadmap_refs", "design_refs"]
                    if record["status"] == "implemented":
                        fields += [
                            "implementation_refs",
                            "verification_refs",
                            "validation_refs",
                            "risk_refs",
                        ]
                    assert all(record.get(f) for f in fields)
                    design_refs.update(record["design_refs"])
                    if record["status"] == "deferred":
                        assert record["deferral_reason"] and record["reconsideration_trigger"]
                if kind == "work_items":
                    assert set(record["requirement_ids"]) <= requirements
                    assert record["status"] in {
                        "proposed",
                        "approved",
                        "in-progress",
                        "verified",
                        "closed",
                        "blocked",
                    }
                    assert record["acceptance_refs"] and record["roadmap_refs"]
                    if record["status"] in {"approved", "in-progress", "verified", "closed"}:
                        assert re.fullmatch(
                            r"conversation:\d{4}-\d{2}-\d{2}-[a-z0-9-]+", record["approval_ref"]
                        )
                    if record["status"] in {"verified", "closed"}:
                        assert record["evidence_refs"]
                for key, refs in record.items():
                    if not key.endswith("_refs"):
                        continue
                    for ref in refs:
                        path = PurePosixPath(ref)
                        assert not path.is_absolute() and ".." not in path.parts
                        assert ":" not in ref and "\\" not in ref and ".agents" not in path.parts
                        target = (root / ref).resolve()
                        assert target.is_relative_to(root.resolve()) and target.is_file()
        for adr in (root / "docs/architecture/decisions").glob("*.md"):
            if "Status: accepted" in adr.read_text("utf-8"):
                assert adr.relative_to(root).as_posix() in design_refs
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        errors.append("registry.invalid")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    findings = check(Path(__file__).resolve().parents[1], args.as_of)
    print(json.dumps({"status": "fail" if findings else "pass", "findings": findings}))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
