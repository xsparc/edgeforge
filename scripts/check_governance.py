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
        if not (data["schema_version"] == 1 and data["project"] == "edgeforge"):
            raise ValueError("invalid registry")
        if data["authority"]["dhf_is_authoritative"] is not False:
            raise ValueError("invalid registry")
        expected_priority = [
            "docs/architecture/overview.md",
            "docs/roadmap/implementation-roadmap.md",
            "docs/architecture/decisions/",
            "code-and-tests",
            "supporting-documentation",
        ]
        if data["authority"]["source_priority"] != expected_priority:
            raise ValueError("invalid authority order")
        reviewed = date.fromisoformat(data["review"]["last_reviewed"])
        due = date.fromisoformat(data["review"]["review_due"])
        if not reviewed <= due:
            raise ValueError("invalid registry")
        if as_of and as_of > due:
            errors.append("review.overdue")
        objectives = {r["id"] for r in data["objectives"]}
        requirements = {r["id"] for r in data["requirements"]}
        if not objectives or not requirements or not data["work_items"]:
            raise ValueError("missing evidence records")
        seen = set()
        design_refs = set()
        for kind in ("objectives", "requirements", "work_items", "research_decisions"):
            for record in data[kind]:
                identity = record["id"]
                if not re.fullmatch("[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", identity):
                    raise ValueError("invalid registry")
                if identity in seen:
                    raise ValueError("invalid registry")
                seen.add(identity)
                if kind == "requirements":
                    if not record["objective_ids"]:
                        raise ValueError("missing objective link")
                    if not set(record["objective_ids"]) <= objectives:
                        raise ValueError("invalid registry")
                    if record["status"] not in {"planned", "implemented", "deferred", "retired"}:
                        raise ValueError("invalid registry")
                    fields = ["roadmap_refs", "design_refs"]
                    if record["status"] == "implemented":
                        fields += [
                            "implementation_refs",
                            "verification_refs",
                            "validation_refs",
                            "risk_refs",
                        ]
                    if not all(record.get(f) for f in fields):
                        raise ValueError("invalid registry")
                    design_refs.update(record["design_refs"])
                    if record["status"] == "deferred":
                        if not (record["deferral_reason"] and record["reconsideration_trigger"]):
                            raise ValueError("invalid registry")
                if kind == "work_items":
                    if not record["requirement_ids"]:
                        raise ValueError("missing requirement link")
                    if not set(record["requirement_ids"]) <= requirements:
                        raise ValueError("invalid registry")
                    if record["status"] not in {
                        "proposed",
                        "approved",
                        "in-progress",
                        "verified",
                        "closed",
                        "blocked",
                    }:
                        raise ValueError("invalid registry")
                    if not (record["acceptance_refs"] and record["roadmap_refs"]):
                        raise ValueError("invalid registry")
                    if record["status"] in {"approved", "in-progress", "verified", "closed"}:
                        if not re.fullmatch(
                            "conversation:\\d{4}-\\d{2}-\\d{2}-[a-z0-9-]+", record["approval_ref"]
                        ):
                            raise ValueError("invalid registry")
                    if record["status"] in {"verified", "closed"}:
                        if not record["evidence_refs"]:
                            raise ValueError("invalid registry")
                for key, refs in record.items():
                    if not key.endswith("_refs"):
                        continue
                    for ref in refs:
                        path = PurePosixPath(ref)
                        if not (not path.is_absolute() and ".." not in path.parts):
                            raise ValueError("invalid registry")
                        if not (
                            ":" not in ref and "\\" not in ref and (".agents" not in path.parts)
                        ):
                            raise ValueError("invalid registry")
                        target = (root / ref).resolve()
                        if not (target.is_relative_to(root.resolve()) and target.is_file()):
                            raise ValueError("invalid registry")
        for adr in (root / "docs/architecture/decisions").glob("*.md"):
            if "Status: accepted" in adr.read_text("utf-8"):
                if adr.relative_to(root).as_posix() not in design_refs:
                    raise ValueError("invalid registry")
    except (OSError, ValueError, KeyError, TypeError):
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
