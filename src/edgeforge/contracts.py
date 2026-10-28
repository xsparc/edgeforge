"""Versioned, JSON-serializable contracts shared by the SDK, CLI, and service."""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,63}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class TensorSpec(Contract):
    name: Name
    dtype: Literal["float32", "float64", "int32", "int64", "uint8", "bool"]
    shape: list[Annotated[int, Field(ge=1, le=1_000_000)]] = Field(max_length=8)

    @model_validator(mode="after")
    def bounded(self):
        if math.prod(self.shape) > 16_000_000:
            raise ValueError("tensor exceeds element limit")
        return self


class Affine(Contract):
    scale: float = 1.0
    offset: float = 0.0


class ModelConfig(Contract):
    schema_version: Literal[1] = 1
    runtime: Literal["onnx", "executorch"]
    inputs: list[TensorSpec] = Field(min_length=1, max_length=32)
    outputs: list[TensorSpec] = Field(min_length=1, max_length=32)
    preprocessing: dict[Name, Affine] = Field(default_factory=dict)
    provider: str = Field(default="CPUExecutionProvider", min_length=1, max_length=80)
    threads: int = Field(default=1, ge=1, le=64)

    @model_validator(mode="after")
    def consistent(self):
        for specs in (self.inputs, self.outputs):
            if len({s.name for s in specs}) != len(specs):
                raise ValueError("tensor names must be unique within inputs and outputs")
        inputs = {s.name: s for s in self.inputs}
        for name in self.preprocessing:
            if name not in inputs or inputs[name].dtype not in {"float32", "float64"}:
                raise ValueError("preprocessing requires a named floating-point input")
        if self.runtime == "executorch" and self.provider != "portable":
            raise ValueError("ExecuTorch requires the portable provider label")
        return self


class Asset(Contract):
    sha256: Digest
    size_bytes: int = Field(ge=1, le=512 * 1024 * 1024)


class Manifest(Contract):
    schema_version: Literal[1] = 1
    config: ModelConfig
    model: Asset
    vectors: Asset
    quantization: Literal["none", "dynamic-int8"] = "none"
    source_model_sha256: Digest
    producer_version: str = "0.1.0"


class BenchmarkOptions(Contract):
    warmup: int = Field(default=5, ge=0, le=100)
    iterations: int = Field(default=50, ge=1, le=10_000)
    atol: float = Field(default=1e-5, ge=0, le=1)
    rtol: float = Field(default=1e-4, ge=0, le=1)
