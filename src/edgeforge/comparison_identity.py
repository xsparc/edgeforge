"""Versioned canonical retention encoding; this is not RFC 8785/JCS."""

import hashlib
import hmac
import json
import re
from typing import Literal

from pydantic import Field, field_validator

from .comparison import MAX_COMPARISON_BYTES, ReportComparison
from .comparison_review import _decode, read_comparison
from .contracts import Contract
from .errors import EdgeForgeError

ENCODING = "edgeforge-comparison-json-v1"
MAX_IDENTITY_BYTES = 4096


class ComparisonIdentity(Contract):
    schema_version: Literal[1]
    canonicalization: Literal["edgeforge-comparison-json-v1"]
    comparison_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1, le=MAX_COMPARISON_BYTES)
    interpretation: Literal["retained_identity_not_attestation"]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("identity version must be an integer")
        return value


def read_identity(raw: bytes) -> ComparisonIdentity:
    return ComparisonIdentity.model_validate(_decode(raw, MAX_IDENTITY_BYTES))


def verify_identity_record(comparison: ReportComparison, identity: ComparisonIdentity) -> None:
    # Revalidate caller-owned SDK models before trusting their constraints.
    retained = ComparisonIdentity.model_validate(identity.model_dump())
    actual = comparison_identity(comparison)
    if retained.bytes != actual["bytes"] or not hmac.compare_digest(
        retained.comparison_sha256, actual["comparison_sha256"]
    ):
        raise EdgeForgeError("retained comparison identity differs")


def canonical_comparison(comparison: ReportComparison) -> bytes:
    checked = ReportComparison.model_validate(comparison.model_dump())
    raw = (
        json.dumps(
            checked.model_dump(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(raw) > MAX_COMPARISON_BYTES:
        raise EdgeForgeError("canonical comparison exceeds byte limit")
    # Apply the retained reader's Unicode and complete-envelope rules to SDK inputs too.
    read_comparison(raw)
    return raw


def comparison_identity(comparison: ReportComparison) -> dict:
    raw = canonical_comparison(comparison)
    return ComparisonIdentity.model_validate(
        {
            "schema_version": 1,
            "canonicalization": ENCODING,
            "comparison_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "interpretation": "retained_identity_not_attestation",
        }
    ).model_dump()


def verify_expected_identity(comparison: ReportComparison, expected: str) -> None:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise EdgeForgeError("invalid expected digest")
    actual = comparison_identity(comparison)["comparison_sha256"]
    if not hmac.compare_digest(actual, expected):
        raise EdgeForgeError("comparison identity differs")
