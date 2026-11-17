"""Closed retained identities for the versioned comparison bundle encoding."""

import hmac
from typing import Literal

from pydantic import Field, field_validator

from .comparison_bundle import MAX_COMPARISON_BUNDLE_BYTES, ComparisonBundle, bundle_identity
from .comparison_review import _decode
from .contracts import Contract
from .errors import EdgeForgeError

MAX_IDENTITY_BYTES = 4096


class BundleIdentity(Contract):
    schema_version: Literal[1]
    encoding: Literal["edgeforge-comparison-bundle-json-v1"]
    bundle_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1, le=MAX_COMPARISON_BUNDLE_BYTES)
    interpretation: Literal["normalized_bundle_identity_not_attestation"]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("identity version must be an integer")
        return value


def read_identity(raw: bytes) -> BundleIdentity:
    return BundleIdentity.model_validate(_decode(raw, MAX_IDENTITY_BYTES))


def verify_identity_record(bundle: ComparisonBundle, identity: BundleIdentity) -> None:
    retained = BundleIdentity.model_validate(identity.model_dump())
    actual = bundle_identity(bundle)
    if retained.bytes != actual["bytes"] or not hmac.compare_digest(
        retained.bundle_sha256, actual["bundle_sha256"]
    ):
        raise EdgeForgeError("retained bundle identity differs")
