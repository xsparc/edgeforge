"""Versioned canonical retention encoding; this is not RFC 8785/JCS."""

import hashlib
import hmac
import json
import re

from .comparison import MAX_COMPARISON_BYTES, ReportComparison
from .comparison_review import read_comparison
from .errors import EdgeForgeError

ENCODING = "edgeforge-comparison-json-v1"


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
    return {
        "schema_version": 1,
        "canonicalization": ENCODING,
        "comparison_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "interpretation": "retained_identity_not_attestation",
    }


def verify_expected_identity(comparison: ReportComparison, expected: str) -> None:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise EdgeForgeError("invalid expected digest")
    actual = comparison_identity(comparison)["comparison_sha256"]
    if not hmac.compare_digest(actual, expected):
        raise EdgeForgeError("comparison identity differs")
