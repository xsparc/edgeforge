"""Bounded offline review of retained reports, without native model execution."""

import csv
import io
import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .benchmark import BenchmarkReport
from .bundle import MAX_BUNDLE_BYTES, MAX_MODEL_BYTES, Bundle, load_vectors
from .contracts import Contract, Digest
from .errors import EdgeForgeError

MAX_REPORT_BYTES = 256 * 1024
Label = Annotated[str, Field(min_length=1, max_length=200)]
Nonnegative = Annotated[int, Field(ge=0)]


class Latency(Contract):
    min: float = Field(ge=0)
    mean: float = Field(ge=0)
    p50: float = Field(ge=0)
    p95: float = Field(ge=0)
    max: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if (
            not self.min <= self.p50 <= self.p95 <= self.max
            or not self.min <= self.mean <= self.max
        ):
            raise ValueError("inconsistent latency summary")
        return self


class Memory(Contract):
    rss_before_load_bytes: Nonnegative
    rss_sampled_peak_bytes: Nonnegative
    rss_sampled_increase_bytes: Nonnegative
    scope: Literal["whole-process RSS sampled after load and inference; not device VRAM"]

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.rss_sampled_peak_bytes - self.rss_before_load_bytes
            != self.rss_sampled_increase_bytes
        ):
            raise ValueError("inconsistent sampled RSS")
        return self


class Storage(Contract):
    model_bytes: int = Field(ge=1, le=MAX_MODEL_BYTES)
    bundle_bytes: int = Field(ge=1, le=MAX_BUNDLE_BYTES)

    @model_validator(mode="after")
    def consistent(self):
        if self.bundle_bytes <= self.model_bytes:
            raise ValueError("bundle must contain model and metadata")
        return self


class Agreement(Contract):
    passed: bool
    finite: bool
    elements_compared: int = Field(ge=1)
    elements_matching: Nonnegative
    fraction_matching: float = Field(ge=0, le=1)
    max_abs_error: float = Field(ge=0)
    scope: Literal["golden-output numerical agreement; not task-level accuracy"]

    @model_validator(mode="after")
    def consistent(self):
        if self.elements_matching > self.elements_compared:
            raise ValueError("matching count exceeds compared count")
        if self.fraction_matching != self.elements_matching / self.elements_compared:
            raise ValueError("inconsistent agreement fraction")
        if self.passed != (self.finite and self.elements_matching == self.elements_compared):
            raise ValueError("inconsistent agreement verdict")
        return self


class Packages(Contract):
    numpy: Label | None
    onnxruntime: Label | None
    onnx: Label | None
    executorch: Label | None
    torch: Label | None
    psutil: Label | None


class Device(Contract):
    schema_version: Literal[1]
    os: Label
    architecture: Label
    python: Label
    logical_cpus: Annotated[int, Field(ge=1)] | None
    system_ram_bytes: Nonnegative
    packages: Packages
    onnx_registered_providers: list[Label] = Field(max_length=64)
    accelerator_verification: Literal["not-probed"]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("version must be an integer")
        return value


class ReportEvidence(BenchmarkReport):
    """Strict reader for the existing v1 wire format; benchmark output is unchanged."""

    schema_version: Literal[1] = 1
    edgeforge_version: Label
    bundle_sha256: Digest
    measured_at: str = Field(min_length=1, max_length=64)
    runtime: Literal["onnx", "executorch"]
    runtime_version: Label
    requested_provider: Label
    active_providers: list[Label] = Field(min_length=1, max_length=64)
    threads: Annotated[int, Field(ge=1, le=64)] | None
    cases: int = Field(ge=1, le=100_000)
    latency_ms: Latency
    memory: Memory
    storage: Storage
    agreement: Agreement
    device: Device
    measurement_scope: Literal[
        "serial adapter call including tensor conversion and materialization; "
        "excludes model load, preprocessing, RSS sampling and comparison"
    ]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value):
        if type(value) is not int:
            raise ValueError("version must be an integer")
        return value

    @model_validator(mode="after")
    def consistent(self):
        if datetime.fromisoformat(self.measured_at).utcoffset() is None:
            raise ValueError("measurement timestamp requires a timezone")
        if self.cases * (self.options.warmup + self.options.iterations) > 100_000:
            raise ValueError("invocation budget exceeded")
        if (self.threads is None) != (self.runtime == "executorch"):
            raise ValueError("thread scope differs from runtime")
        if self.runtime == "executorch" and self.requested_provider != "portable":
            raise ValueError("invalid ExecuTorch provider")
        if self.agreement.elements_compared % (self.cases * self.options.iterations):
            raise ValueError("compared elements differ from measurement count")
        return self


def validate_report(raw: bytes) -> ReportEvidence:
    if len(raw) > MAX_REPORT_BYTES:
        raise EdgeForgeError("report exceeds byte limit")
    return ReportEvidence.model_validate_json(raw)


def verify_report_bundle(report: ReportEvidence, bundle: Bundle) -> None:
    """Check source identity and declared counts, not measured performance or provenance."""
    report = ReportEvidence.model_validate(report.model_dump())
    config = bundle.manifest.config
    vectors = load_vectors(bundle.vectors, config)
    cases = len(vectors[f"input__{config.inputs[0].name}"])
    elements = sum(math.prod(spec.shape) for spec in config.outputs)
    if (
        report.bundle_sha256 != bundle.sha256
        or report.runtime != config.runtime
        or report.requested_provider != config.provider
        or report.threads != (config.threads if config.runtime == "onnx" else None)
        or report.storage.model_bytes != len(bundle.model)
        or report.storage.bundle_bytes != bundle.size_bytes
        or report.cases != cases
        or report.agreement.elements_compared != elements * cases * report.options.iterations
    ):
        raise EdgeForgeError("report differs from retained bundle")


def render_report_csv(report: ReportEvidence) -> str:
    report = ReportEvidence.model_validate(report.model_dump())
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(
        [
            "schema_version",
            "bundle_sha256",
            "measured_at_text",
            "runtime",
            "runtime_version_text",
            "requested_provider_text",
            "active_providers_text",
            "cases",
            "warmup",
            "iterations",
            "min_ms",
            "mean_ms",
            "p50_ms",
            "p95_ms",
            "max_ms",
            "rss_sampled_peak_bytes",
            "model_bytes",
            "bundle_bytes",
            "agreement_passed",
            "elements_compared",
            "elements_matching",
            "fraction_matching",
            "max_abs_error",
            "interpretation",
        ]
    )
    writer.writerow(
        [
            1,
            report.bundle_sha256,
            "text:" + report.measured_at,
            report.runtime,
            "text:" + report.runtime_version,
            "text:" + report.requested_provider,
            "text:" + ";".join(report.active_providers),
            report.cases,
            report.options.warmup,
            report.options.iterations,
            report.latency_ms.min,
            report.latency_ms.mean,
            report.latency_ms.p50,
            report.latency_ms.p95,
            report.latency_ms.max,
            report.memory.rss_sampled_peak_bytes,
            report.storage.model_bytes,
            report.storage.bundle_bytes,
            str(report.agreement.passed).lower(),
            report.agreement.elements_compared,
            report.agreement.elements_matching,
            report.agreement.fraction_matching,
            report.agreement.max_abs_error,
            "retained_measurement_not_independent_attestation",
        ]
    )
    output = stream.getvalue()
    if len(output.encode("utf-8")) > MAX_REPORT_BYTES:
        raise EdgeForgeError("CSV exceeds byte limit")
    return output
