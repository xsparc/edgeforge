"""Directional, descriptive comparisons of retained evidence; never execute models."""

import csv
import hashlib
import io
import json
from typing import Literal

from pydantic import field_validator, model_validator

from .contracts import Contract, Digest
from .reports import ReportEvidence

MAX_COMPARISON_BYTES = 512 * 1024
Reason = Literal[
    "bundle",
    "options",
    "runtime",
    "runtime_version",
    "requested_provider",
    "active_providers",
    "threads",
    "cases",
    "device",
    "edgeforge_version",
]
REASONS = (
    "bundle",
    "options",
    "runtime",
    "runtime_version",
    "requested_provider",
    "active_providers",
    "threads",
    "cases",
    "device",
    "edgeforge_version",
)


class LatencyDelta(Contract):
    min: float
    mean: float
    p50: float
    p95: float
    max: float


class MemoryDelta(Contract):
    rss_before_load_bytes: int
    rss_sampled_peak_bytes: int
    rss_sampled_increase_bytes: int


class StorageDelta(Contract):
    model_bytes: int
    bundle_bytes: int


def report_digest(report: ReportEvidence) -> str:
    """SHA-256 of normalized, sorted, compact UTF-8 JSON, not original file bytes."""
    normalized = json.dumps(
        report.model_dump(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def reasons(before: ReportEvidence, after: ReportEvidence) -> list[str]:
    return [
        name
        for name in REASONS
        if getattr(before, "bundle_sha256" if name == "bundle" else name)
        != getattr(after, "bundle_sha256" if name == "bundle" else name)
    ]


def delta(before, after, model):
    return model.model_validate(
        {name: getattr(after, name) - getattr(before, name) for name in model.model_fields}
    )


class ReportComparison(Contract):
    schema_version: Literal[1] = 1
    direction: Literal["after_minus_before"] = "after_minus_before"
    before: ReportEvidence
    after: ReportEvidence
    before_report_sha256: Digest
    after_report_sha256: Digest
    compatible: bool
    incompatibility_reasons: list[Reason]
    latency_ms_delta: LatencyDelta
    memory_delta: MemoryDelta
    storage_delta: StorageDelta
    interpretation: Literal["descriptive_only_no_performance_verdict"] = (
        "descriptive_only_no_performance_verdict"
    )
    hardware_identity: Literal["not_established"] = "not_established"

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("version must be an integer")
        return value

    @model_validator(mode="after")
    def consistent(self):
        # Revalidate nested instances too: SDK callers may have mutated them.
        before = ReportEvidence.model_validate(self.before.model_dump())
        after = ReportEvidence.model_validate(self.after.model_dump())
        expected = reasons(before, after)
        if (
            self.before_report_sha256 != report_digest(before)
            or self.after_report_sha256 != report_digest(after)
            or self.incompatibility_reasons != expected
            or self.compatible != (not expected)
            or self.latency_ms_delta != delta(before.latency_ms, after.latency_ms, LatencyDelta)
            or self.memory_delta != delta(before.memory, after.memory, MemoryDelta)
            or self.storage_delta != delta(before.storage, after.storage, StorageDelta)
        ):
            raise ValueError("comparison differs from retained reports")
        return self


def compare_reports(before: ReportEvidence, after: ReportEvidence) -> ReportComparison:
    before = ReportEvidence.model_validate(before.model_dump())
    after = ReportEvidence.model_validate(after.model_dump())
    differences = reasons(before, after)
    return ReportComparison(
        before=before,
        after=after,
        before_report_sha256=report_digest(before),
        after_report_sha256=report_digest(after),
        compatible=not differences,
        incompatibility_reasons=differences,
        latency_ms_delta=delta(before.latency_ms, after.latency_ms, LatencyDelta),
        memory_delta=delta(before.memory, after.memory, MemoryDelta),
        storage_delta=delta(before.storage, after.storage, StorageDelta),
    )


def render_comparison_csv(comparison: ReportComparison) -> str:
    comparison = ReportComparison.model_validate(comparison.model_dump())
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(
        [
            "schema_version",
            "direction",
            "before_report_sha256",
            "after_report_sha256",
            "compatible",
            "incompatibility_reasons",
            "before_runtime_version_text",
            "after_runtime_version_text",
            "group",
            "metric",
            "before",
            "after",
            "delta",
            "interpretation",
            "hardware_identity",
        ]
    )
    for group, changes in [
        ("latency_ms", comparison.latency_ms_delta),
        ("memory", comparison.memory_delta),
        ("storage", comparison.storage_delta),
    ]:
        for metric, change in changes.model_dump().items():
            writer.writerow(
                [
                    1,
                    comparison.direction,
                    comparison.before_report_sha256,
                    comparison.after_report_sha256,
                    str(comparison.compatible).lower(),
                    ";".join(comparison.incompatibility_reasons),
                    "text:" + comparison.before.runtime_version,
                    "text:" + comparison.after.runtime_version,
                    group,
                    metric,
                    getattr(getattr(comparison.before, group), metric),
                    getattr(getattr(comparison.after, group), metric),
                    change,
                    comparison.interpretation,
                    comparison.hardware_identity,
                ]
            )
    return stream.getvalue()
