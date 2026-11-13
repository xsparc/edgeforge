"""Closed portable report/comparison evidence; validation never runs inference."""

import json
from typing import Literal

from pydantic import field_validator, model_validator

from .comparison import MAX_COMPARISON_BYTES, ReportComparison, compare_reports
from .comparison_review import _decode, read_comparison, read_source
from .contracts import Contract
from .errors import EdgeForgeError
from .reports import MAX_REPORT_BYTES, ReportEvidence

# Includes bounded component JSON plus a small fixed envelope allowance.
MAX_COMPARISON_BUNDLE_BYTES = 2 * MAX_REPORT_BYTES + MAX_COMPARISON_BYTES + 4096


def compact(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


class ComparisonBundle(Contract):
    schema_version: Literal[1]
    before: ReportEvidence
    after: ReportEvidence
    comparison: ReportComparison
    interpretation: Literal["local_source_consistency_only"]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("version must be an integer")
        return value

    @model_validator(mode="before")
    @classmethod
    def closed_components(cls, data):
        # Keep strict retained readers' required-field and byte-limit contracts.
        if not isinstance(data, dict) or set(data) != set(cls.model_fields):
            raise ValueError("incomplete bundle envelope")
        read_source(compact(data["before"]))
        read_source(compact(data["after"]))
        read_comparison(compact(data["comparison"]))
        return data

    @model_validator(mode="after")
    def consistent(self):
        if self.comparison != compare_reports(self.before, self.after):
            raise ValueError("comparison differs from retained reports")
        return self


def create_bundle(before: ReportEvidence, after: ReportEvidence) -> ComparisonBundle:
    a = read_source(compact(before.model_dump()))
    b = read_source(compact(after.model_dump()))
    return ComparisonBundle.model_validate(
        {
            "schema_version": 1,
            "before": a.model_dump(),
            "after": b.model_dump(),
            "comparison": compare_reports(a, b).model_dump(),
            "interpretation": "local_source_consistency_only",
        }
    )


def encode_bundle(bundle: ComparisonBundle) -> bytes:
    checked = ComparisonBundle.model_validate(bundle.model_dump())
    raw = compact(checked.model_dump()) + b"\n"
    if len(raw) > MAX_COMPARISON_BUNDLE_BYTES:
        raise EdgeForgeError("bundle exceeds byte limit")
    return raw


def read_bundle(raw: bytes) -> ComparisonBundle:
    return ComparisonBundle.model_validate(_decode(raw, MAX_COMPARISON_BUNDLE_BYTES))
